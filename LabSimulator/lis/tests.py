"""Simulator tests: python manage.py test. mllp.send is replaced, so no LiverLink is needed."""
import json
from unittest.mock import patch

from django.test import TestCase

from . import hl7, mllp, services
from .models import Message, Order


def orm(control='NW', order_id='12', mrn='LL-000001', control_id='LL1', tests=('1742-6^ALT', '1975-2^Bilirubin'),
        message_type='ORM^O01^ORM_O01'):
    lines = [f'MSH|^~\\&|LIVERLINK|LIVER_CENTER|EXTERNAL_LAB||20261125100000+0000||{message_type}|{control_id}|P|2.5',
             f'PID|1||{mrn}^^^LIVERLINK^MR||Sa\\T\\lem^Hoda||19650101|F']
    for i, test in enumerate(tests, start=1):
        lines += [f'ORC|{control}|{order_id}^LIVERLINK||||||||||5^Nabil^Sara',
                  f'OBR|{i}|{order_id}^LIVERLINK||{test}^LN|A']
    return '\r'.join(lines) + '\r'


def answer(code, text=''):
    """A fake LiverLink that answers every message with `code`."""
    return lambda host, port, raw: hl7.build_ack(hl7.read_header(hl7.parse(raw)), code, text)


class IncomingOrderTests(TestCase):
    def receive(self, raw):
        code, text, _ = hl7.parse_ack(services.handle_inbound(raw))
        return code, text

    def test_new_order(self):
        self.assertEqual(hl7.parse_ack(services.handle_inbound(orm())), ('AA', '', 'LL1'))
        order = Order.objects.get()
        self.assertRegex(order.accession_number, r'^ACC-\d{8}-\d{4}$')
        self.assertEqual((order.mrn, order.placer_order_id, order.last_name, order.ordered_by, order.priority),
                         ('LL-000001', '12', 'Sa&lem', 'Sara Nabil', 'urgent'))
        self.assertEqual(list(order.tests.values_list('code', 'unit', 'reference_range')),
                         [('1742-6', 'U/L', '7-56'), ('1975-2', 'mg/dL', '0.1-1.2')])
        self.assertEqual(Message.objects.get().status, 'processed')

    def test_same_message_twice_creates_one_order(self):
        self.receive(orm())
        self.assertEqual(self.receive(orm())[0], 'AA')
        self.assertEqual((Order.objects.count(), Message.objects.count()), (1, 1))

    def test_refused_messages(self):
        self.receive(orm())
        for name, raw, code in [
            ('not HL7', 'hello', 'AR'), ('empty', '', 'AR'),
            ('unsupported type', orm(control_id='a', message_type='ADT^A04'), 'AR'),
            ('no control id', orm(control_id=''), 'AR'),
            ('same order again', orm(control_id='b'), 'AE'),
            ('no MRN', orm(control_id='c', order_id='13', mrn=''), 'AE'),
            ('no tests', orm(control_id='d', order_id='13', tests=()), 'AE'),
            ('unknown control', orm(control_id='e', order_id='13', control='XX'), 'AE'),
            ('cancel unknown order', orm(control_id='f', order_id='99', control='CA'), 'AE'),
            ('cancel with another MRN', orm(control_id='g', mrn='LL-2', control='CA'), 'AE'),
        ]:
            with self.subTest(name):
                self.assertEqual(self.receive(raw)[0], code)
        self.assertEqual(Order.objects.get().status, 'received')

    def test_cancel(self):
        self.receive(orm())
        self.assertEqual(self.receive(orm('CA', control_id='LL2'))[0], 'AA')
        self.assertEqual(Order.objects.get().status, 'cancelled')


class WorkflowTests(TestCase):
    def setUp(self):
        services.handle_inbound(orm())
        self.order = Order.objects.get()
        self.url = f'/api/orders/{self.order.pk}/'

    def post(self, path, data=None):
        return self.client.post(self.url + path, json.dumps(data or {}), content_type='application/json')

    def results(self, *values, **extra):
        return {'results': [dict(id=t.pk, value=v, unit=t.unit, reference_range=t.reference_range, flag='N') | extra
                            for t, v in zip(self.order.tests.all(), values)]}

    def complete(self):
        self.post('status/', {'status': 'processing'})
        self.post('results/', self.results('30', '0.9'))
        r = self.post('status/', {'status': 'completed'})
        self.assertEqual(r.status_code, 200, r.content)

    def test_page_and_lists(self):
        self.assertContains(self.client.get('/'), 'External Laboratory')
        self.assertEqual(self.client.get('/api/orders/').json()['orders'][0]['mrn'], 'LL-000001')
        self.assertEqual(len(self.client.get(self.url).json()['tests']), 2)
        msg = self.client.get('/api/messages/').json()['messages'][0]
        self.assertIn('ORC|NW', self.client.get(f'/api/messages/{msg["id"]}/').json()['raw_message'])

    def test_status_order_is_enforced(self):
        for status in ('completed', 'cancelled', 'nonsense', None, ['processing'], {}):
            self.assertEqual(self.post('status/', {'status': status}).status_code, 400, status)
        self.assertEqual(self.post('results/', self.results('1', '1')).status_code, 400)  # not processing yet
        self.assertEqual(self.post('status/', {'status': 'processing'}).status_code, 200)
        self.assertEqual(self.post('status/', {'status': 'completed'}).status_code, 400)  # no results yet
        self.assertEqual(self.post('send/').status_code, 400)                             # not completed yet

    def test_invalid_results(self):
        self.post('status/', {'status': 'processing'})
        for value in ('abc', '-1', '1e5', 'NaN', '1.2.3', '²', '9' * 13):
            self.assertEqual(self.post('results/', self.results(value)).status_code, 400, value)
        self.assertEqual(self.post('results/', self.results('1', flag='')).status_code, 400)
        self.assertEqual(self.post('results/', {'results': [{'id': 9999, 'value': '1'}]}).status_code, 400)
        for bad in ('x', ['x'], [{'id': []}], [{}]):
            self.assertEqual(self.post('results/', {'results': bad}).status_code, 400, bad)
        self.assertFalse(self.order.tests.exclude(value='').exists())

    def test_send_results(self):
        self.complete()
        with patch.object(mllp, 'send', side_effect=answer('AA')) as send:
            self.assertEqual(self.post('send/').status_code, 200)
            self.assertEqual(self.post('send/').status_code, 400)  # only once
        self.assertEqual(send.call_count, 1)
        raw = send.call_args.args[2]
        self.assertIn('PID|1||LL-000001^^^LIVERLINK^MR||Sa\\T\\lem^Hoda', raw)
        self.assertIn(f'OBR|1|12^LIVERLINK|{self.order.accession_number}^EXTERNAL_LAB|1742-6^ALT^LN', raw)
        self.assertIn('OBX|1|NM|1742-6^ALT^LN||30|U/L|7-56|N|||F|', raw)
        log = Message.objects.first()
        self.assertEqual((log.direction, log.status, log.ack_code), ('outbound', 'sent', 'AA'))

    def test_refused_or_unreachable_can_be_corrected_and_sent_again(self):
        self.complete()
        for fake in (answer('AE', 'wrong unit'), mllp.MLLPError('No answer'),
                     lambda host, port, raw: hl7.build_ack({'control_id': 'OTHER'}, 'AA')):
            with patch.object(mllp, 'send', side_effect=fake):
                self.assertEqual(self.post('send/').status_code, 400)
            self.assertEqual(Message.objects.first().status, 'error')
        self.assertEqual(self.post('status/', {'status': 'processing'}).status_code, 200)

    def test_cancelled_order_is_locked(self):
        self.complete()
        services.handle_inbound(orm('CA', control_id='LL2'))
        self.assertEqual(self.post('send/').status_code, 400)
        self.assertEqual(self.post('status/', {'status': 'processing'}).status_code, 400)
