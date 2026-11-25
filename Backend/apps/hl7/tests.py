"""HL7 tests. No test talks to a real lab: mllp.send is replaced, except in MLLPTests (local sockets)."""
import datetime
import threading
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APITestCase

from apps.accounts.models import AuditLog, Staff, User
from apps.labs import services as labs
from apps.labs.models import LabOrder, LabTest
from apps.registry.models import Patient

from . import message as hl7
from . import mllp, services
from .models import ExternalSystem, HL7Message

T = Staff.JobTitle


def make_staff(username, job_title):
    user = User.objects.create_user(username, f'{username}@lh.test', 'Str0ng-Pass!2026',
                                    role=Staff.role_for_job_title(job_title), first_name='Sara', last_name='Nabil')
    return Staff.objects.create(user=user, job_title=job_title)


def make_order(staff, **patient_fields):
    data = dict(first_name='Hoda', last_name='Salem', date_of_birth=datetime.date(1965, 1, 1), sex='female',
                phone='01001234567', category='liver_patient')
    data.update(patient_fields)
    patient = Patient.objects.create(**data)
    bili, _ = LabTest.objects.get_or_create(code='1975-2', defaults=dict(
        name='Bilirubin', unit='mg/dL', normal_min=Decimal('0.1'), normal_max=Decimal('1.2')))
    alt, _ = LabTest.objects.get_or_create(code='1742-6', defaults=dict(
        name='ALT', unit='U/L', normal_min=7, normal_max=56))
    return labs.create_order(patient, staff, [bili, alt])


def oru(order, results=(('1975-2', '3.4', 'mg/dL'), ('1742-6', '30', 'U/L')), mrn=None, control_id='LAB1',
        sender='EXTERNAL_LAB', message_type='ORU^R01', order_id=None, status='F', value_type='NM'):
    order_id = order.pk if order_id is None else order_id
    lines = [f'MSH|^~\\&|{sender}|LAB|LIVERLINK||20261125100000+0000||{message_type}|{control_id}|P|2.5',
             f'PID|1||{mrn or order.patient.mrn}^^^LIVERLINK^MR||Salem^Hoda']
    for i, (code, value, unit) in enumerate(results, start=1):
        lines += [f'OBR|{i}|{order_id}^LIVERLINK|ACC-1^LAB|{code}^x^LN',
                  f'OBX|1|{value_type}|{code}^x^LN||{value}|{unit}|1-2|N|||{status}|||20261125095500+0000']
    return '\r'.join(lines) + '\r'


def ack_for(raw, code='AA', text=''):
    return hl7.build_ack(hl7.read_header(hl7.parse(raw)), code, text)


@override_settings(HL7_SEND_ASYNC=False)
class OutboundTests(TestCase):
    def setUp(self):
        self.doctor = make_staff('doc', T.HEPATOLOGIST)

    def place(self, send, **patient_fields):
        with patch.object(mllp, 'send', side_effect=send) as mock, self.captureOnCommitCallbacks(execute=True):
            order = make_order(self.doctor, **patient_fields)
        return order, HL7Message.objects.latest('id'), mock

    def test_order_sends_orm_and_records_ack(self):
        order, msg, mock = self.place(lambda host, port, raw: ack_for(raw))
        self.assertEqual(mock.call_args.args[:2], ('127.0.0.1', 2576))
        self.assertEqual((msg.direction, msg.message_type, msg.status, msg.ack_code),
                         ('outbound', 'ORM^O01', 'sent', 'AA'))
        self.assertEqual(msg.patient, order.patient)
        segments = hl7.parse(msg.raw_message).children
        pid = next(s for s in segments if s.name == 'PID')
        self.assertEqual(hl7.field(pid, 'pid_3'), order.patient.mrn)
        obrs = [s for s in segments if s.name == 'OBR']
        self.assertEqual({hl7.field(s, 'obr_4') for s in obrs}, {'1975-2', '1742-6'})
        self.assertEqual({hl7.field(s, 'obr_2') for s in obrs}, {str(order.pk)})

    def test_separators_in_names_are_escaped(self):
        _, msg, _ = self.place(lambda host, port, raw: ack_for(raw), last_name='A|b^c&d~e\\f', first_name='منى')
        pid = next(s for s in hl7.parse(msg.raw_message).children if s.name == 'PID')
        self.assertEqual(hl7.field(pid, 'pid_5', 1), 'A|b^c&d~e\\f')
        self.assertEqual(hl7.field(pid, 'pid_5', 2), 'منى')

    def test_lab_down_keeps_the_order_and_can_be_resent(self):
        order, msg, _ = self.place(mllp.MLLPError('No answer'))
        self.assertEqual(order.status, 'ordered')
        self.assertEqual((msg.status, msg.error_text), ('error', 'No answer'))
        with patch.object(mllp, 'send', side_effect=lambda host, port, raw: ack_for(raw)):
            services.resend(msg)
        msg.refresh_from_db()
        self.assertEqual((msg.status, msg.error_text), ('sent', ''))
        with self.assertRaises(services.ResendError):
            services.resend(msg)  # already delivered

    def test_rejected_by_the_lab(self):
        _, msg, _ = self.place(lambda host, port, raw: ack_for(raw, 'AE', 'No such test'))
        self.assertEqual((msg.status, msg.ack_code, msg.error_text), ('error', 'AE', 'No such test'))

    def test_ack_for_another_message_is_not_accepted(self):
        _, msg, _ = self.place(lambda host, port, raw: hl7.build_ack({'control_id': 'OTHER'}, 'AA'))
        self.assertEqual((msg.status, msg.ack_code), ('error', ''))

    def test_cancel_sends_ca_and_the_failed_new_order_is_not_resent(self):
        order, new, _ = self.place(mllp.MLLPError('down'))
        with patch.object(mllp, 'send', side_effect=lambda host, port, raw: ack_for(raw)) as mock:
            with self.captureOnCommitCallbacks(execute=True):
                labs.cancel_order(order)
            self.assertIn('ORC|CA|', HL7Message.objects.latest('id').raw_message)
            services.resend(new)
            self.assertEqual(mock.call_count, 1)  # only the cancellation went out
        self.assertEqual(new.status, 'error')

    def test_no_active_lab(self):
        ExternalSystem.objects.update(is_active=False)
        make_order(self.doctor)
        self.assertFalse(HL7Message.objects.exists())


class InboundTests(TestCase):
    def setUp(self):
        self.doctor = make_staff('doc', T.HEPATOLOGIST)
        self.order = make_order(self.doctor)
        HL7Message.objects.all().delete()  # the (unsent) order message

    def receive(self, raw):
        code, text, _ = hl7.parse_ack(services.handle_inbound(raw))
        return code, text

    def assertNothingSaved(self):
        self.assertFalse(self.order.results.filter(value__isnull=False).exists())

    def test_results_are_saved_and_acknowledged(self):
        ack = services.handle_inbound(oru(self.order))
        self.assertEqual(hl7.parse_ack(ack), ('AA', '', 'LAB1'))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, LabOrder.Status.RESULTED)
        bili = self.order.results.get(lab_test__code='1975-2')
        self.assertEqual((bili.value, bili.flag, bili.is_released), (Decimal('3.4'), 'high', False))
        self.assertEqual(bili.result_time, datetime.datetime(2026, 11, 25, 9, 55, tzinfo=datetime.timezone.utc))
        log = HL7Message.objects.get()
        self.assertEqual(bili.hl7_message, log)
        self.assertEqual((log.status, log.ack_code, log.patient), ('processed', 'AA', self.order.patient))
        self.assertEqual(AuditLog.objects.filter(entity_type='labs.labresult', actor='HL7: EXTERNAL_LAB').count(), 2)

    def test_partial_results(self):
        self.assertEqual(self.receive(oru(self.order, [('1742-6', '30', 'U/L')]))[0], 'AA')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, LabOrder.Status.PARTIALLY_RESULTED)

    def test_bad_content_is_refused_and_nothing_is_saved(self):
        good = ('1742-6', '30', 'U/L')
        cases = {
            'wrong patient': oru(self.order, mrn='LL-999999'),
            'unknown order': oru(self.order, order_id=999999),
            'order is not a number': oru(self.order, order_id='abc'),
            'unicode digits': oru(self.order, order_id='²'),
            'test not ordered': oru(self.order, [good, ('9999-9', '1', 'U/L')]),
            'repeated test': oru(self.order, [good, good]),
            'wrong unit': oru(self.order, [good, ('1975-2', '58', 'umol/L')]),
            'not a number': oru(self.order, [good, ('1975-2', 'high', 'mg/dL')]),
            'negative': oru(self.order, [good, ('1975-2', '-1', 'mg/dL')]),
            'NaN': oru(self.order, [good, ('1975-2', 'NaN', 'mg/dL')]),
            'too large': oru(self.order, [good, ('1975-2', '1e30', 'mg/dL')]),
            'text type': oru(self.order, value_type='ST'),
            'preliminary': oru(self.order, status='P'),
            'no results': oru(self.order, []),
        }
        for i, (name, raw) in enumerate(cases.items()):
            with self.subTest(name):
                code, text = self.receive(raw.replace('LAB1', f'C{i}'))
                self.assertEqual(code, 'AE')
                self.assertTrue(text)
                self.assertNothingSaved()
                if name == 'wrong unit':  # the patient matched, so the monitor shows it
                    self.assertEqual(HL7Message.objects.latest('id').patient, self.order.patient)
        self.assertEqual(HL7Message.objects.filter(status='error', ack_code='AE').count(), len(cases))

    def test_cancelled_order(self):
        labs.cancel_order(self.order)
        self.assertEqual(self.receive(oru(self.order))[0], 'AE')
        self.assertNothingSaved()

    def test_rejected_messages(self):
        for name, raw in {
            'not HL7': 'hello', 'empty': '',
            'unknown sender': oru(self.order, sender='SOMEONE'),
            'unsupported type': oru(self.order, message_type='ADT^A04'),
            'no control id': oru(self.order, control_id=''),
        }.items():
            with self.subTest(name):
                self.assertEqual(self.receive(raw)[0], 'AR')
        ExternalSystem.objects.update(is_active=False)
        self.assertEqual(self.receive(oru(self.order))[0], 'AR')
        self.assertNothingSaved()
        self.assertEqual(HL7Message.objects.filter(status='error', ack_code='AR').count(), 6)  # all logged

    def test_same_message_twice_is_processed_once(self):
        self.receive(oru(self.order))
        self.assertEqual(self.receive(oru(self.order))[0], 'AA')
        self.assertEqual(HL7Message.objects.count(), 1)

    def test_existing_result_changes_only_by_a_correction(self):
        self.receive(oru(self.order))
        changed = [('1742-6', '99', 'U/L')]
        self.assertEqual(self.receive(oru(self.order, changed, control_id='LAB2'))[0], 'AE')
        self.assertEqual(self.receive(oru(self.order, control_id='LAB3'))[0], 'AA')  # same values again
        self.assertEqual(self.receive(oru(self.order, changed, control_id='LAB4', status='C'))[0], 'AA')
        self.assertEqual(self.order.results.get(lab_test__code='1742-6').value, Decimal('99'))

    def test_unexpected_failure_is_answered_and_rolled_back(self):
        with patch.object(labs, '_on_order_resulted', side_effect=RuntimeError('boom')), \
                self.assertLogs('apps.hl7.services', 'ERROR'):
            code, text = self.receive(oru(self.order))
        self.assertEqual(code, 'AE')
        self.assertNotIn('boom', text)
        self.assertNothingSaved()


class MonitorApiTests(APITestCase):
    def setUp(self):
        self.doctor = make_staff('doc', T.HEPATOLOGIST)
        self.admin = make_staff('boss', T.SUPER_ADMIN)
        self.order = make_order(self.doctor)
        self.msg = HL7Message.objects.get()

    def test_super_admin_only(self):
        urls = ['/api/hl7/messages/', f'/api/hl7/messages/{self.msg.pk}/']
        self.client.force_authenticate(self.doctor.user)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(urls[1] + 'resend/').status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(urls[0]).status_code, 401)

    def test_list_filters_and_detail(self):
        services.handle_inbound(oru(self.order))
        self.client.force_authenticate(self.admin.user)
        r = self.client.get('/api/hl7/messages/').data
        self.assertEqual(r['count'], 2)
        self.assertNotIn('raw_message', r['results'][0])
        for query, count in {'direction=inbound': 1, 'status=queued': 1, 'type=ORU^R01': 1, 'search=LAB1': 1,
                             f'search={self.order.patient.mrn}': 2, 'search=zzz': 0}.items():
            self.assertEqual(self.client.get(f'/api/hl7/messages/?{query}').data['count'], count, query)
        detail = self.client.get(f'/api/hl7/messages/{self.msg.pk}/').data
        self.assertTrue(detail['raw_message'].startswith('MSH|'))
        self.assertTrue(AuditLog.objects.filter(action='view', entity_type='hl7.hl7message').exists())

    def test_resend(self):
        self.client.force_authenticate(self.admin.user)
        with patch.object(mllp, 'send', side_effect=lambda host, port, raw: ack_for(raw)):
            r = self.client.post(f'/api/hl7/messages/{self.msg.pk}/resend/')
            self.assertEqual((r.status_code, r.data['status']), (200, 'sent'))
            self.assertEqual(self.client.post(f'/api/hl7/messages/{self.msg.pk}/resend/').status_code, 400)


class MLLPTests(SimpleTestCase):
    def test_round_trip_over_tcp(self):
        server = mllp.MLLPServer('127.0.0.1', 0, lambda text: f'got {text}')
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            self.assertEqual(mllp.send(*server.server_address, 'MSH|سلام\rPID|1'), 'got MSH|سلام\rPID|1')
        finally:
            server.shutdown()
            server.server_close()

    def test_nobody_listening(self):
        with self.assertRaises(mllp.MLLPError):
            mllp.send('127.0.0.1', 1, 'x', timeout=3)
