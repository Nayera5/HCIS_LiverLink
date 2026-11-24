"""Online payment through Paymob: start, signed callbacks, idempotency and receipts (Paymob API mocked)."""
import datetime
import hashlib
import hmac
from unittest import mock
from urllib.parse import urlencode

from django.test import override_settings
from django.utils import timezone

from apps.registry.test_api import PatientAPITestBase

from . import paymob
from .models import Invoice, InvoiceItem, Payment, Service

PAYMOB = {
    'SECRET_KEY': 'sk_test_x', 'PUBLIC_KEY': 'pk_test_y', 'HMAC_SECRET': 'hmac-secret',
    'INTEGRATION_IDS': [123], 'API_URL': 'https://accept.paymob.test',
    'CHECKOUT_URL': 'https://eg.checkout.paymob.test/', 'CALLBACK_BASE_URL': '',
}
INTENTION = {'id': 'pi_test_1', 'client_secret': 'egy_csk_test_abc', 'intention_order_id': 555}


def transaction_obj(order_id=555, success=True, pending=False, amount_cents=100000, txn_id=9001):
    """Shaped like the sample in Paymob's HMAC docs."""
    return {
        'id': txn_id, 'pending': pending, 'amount_cents': amount_cents, 'success': success,
        'is_auth': False, 'is_capture': False, 'is_standalone_payment': True, 'is_voided': False,
        'is_refunded': False, 'is_3d_secure': True, 'integration_id': 123, 'has_parent_transaction': False,
        'order': {'id': order_id, 'merchant_order_id': None}, 'created_at': '2026-11-24T10:00:00.000000',
        'currency': 'EGP', 'error_occured': False, 'owner': 302852,
        'source_data': {'pan': '2346', 'type': 'card', 'sub_type': 'MasterCard'},
    }


def sign(message):
    return hmac.new(b'hmac-secret', message.encode(), hashlib.sha512).hexdigest()


@override_settings(PAYMOB=PAYMOB)
class PaymobTests(PatientAPITestBase):
    def setUp(self):
        super().setUp()
        service = Service.objects.get(code='CONS-001')  # 1000 EGP
        self.invoice = Invoice.objects.create(patient=self.own, due_date=timezone.localdate())
        InvoiceItem.objects.create(invoice=self.invoice, service=service, quantity=1)
        self.invoice.recompute_total()

    def start(self, user=None, intention=INTENTION):
        self.as_(user or self.pat_user)
        with mock.patch('apps.billing.paymob._post', return_value=intention) as post:
            r = self.client.post(f'/api/invoices/me/{self.invoice.pk}/pay-online/')
        return r, post

    def callback(self, obj, signature=None):
        self.client.force_authenticate(None)
        signature = signature or paymob.hmac_for_processed(obj)
        return self.client.post(f'/api/payments/paymob/callback/?hmac={signature}',
                                {'type': 'TRANSACTION', 'obj': obj}, format='json')

    # ---------------------------------------------------------------- HMAC

    def test_hmac_uses_paymob_field_order_and_lowercase_booleans(self):
        expected = ('100000' '2026-11-24T10:00:00.000000' 'EGP' 'false' 'false' '9001' '123' 'true' 'false'
                    'false' 'false' 'true' 'false' '555' '302852' 'false' '2346' 'MasterCard' 'card' 'true')
        self.assertEqual(paymob.hmac_for_processed(transaction_obj()), sign(expected))

    def test_redirect_hmac_matches_callback_hmac(self):
        obj = transaction_obj()
        params = {'amount_cents': '100000', 'created_at': obj['created_at'], 'currency': 'EGP',
                  'error_occured': 'false', 'has_parent_transaction': 'false', 'id': '9001',
                  'integration_id': '123', 'is_3d_secure': 'true', 'is_auth': 'false', 'is_capture': 'false',
                  'is_refunded': 'false', 'is_standalone_payment': 'true', 'is_voided': 'false',
                  'order': '555', 'owner': '302852', 'pending': 'false', 'source_data.pan': '2346',
                  'source_data.sub_type': 'MasterCard', 'source_data.type': 'card', 'success': 'true'}
        self.assertEqual(paymob.hmac_for_response(params), paymob.hmac_for_processed(obj))
        renamed = {('order_id' if k == 'order' else k.replace('.', '_')): v for k, v in params.items()}
        self.assertEqual(paymob.hmac_for_response(renamed), paymob.hmac_for_processed(obj))

    # ---------------------------------------------------------------- start

    def test_start_creates_pending_payment_and_returns_checkout_url(self):
        r, post = self.start()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['checkout_url'],
                         'https://eg.checkout.paymob.test/?publicKey=pk_test_y&clientSecret=egy_csk_test_abc')
        payment = Payment.objects.get()
        self.assertEqual((payment.method, payment.status, payment.amount, payment.gateway_order_id),
                         ('online', 'pending', self.invoice.total_amount, '555'))
        path, body = post.call_args.args
        self.assertEqual(path, '/v1/intention/')
        self.assertEqual((body['amount'], body['currency'], body['payment_methods']), (100000, 'EGP', [123]))
        self.assertEqual(body['items'][0]['amount'], body['amount'])
        self.assertEqual(body['special_reference'], payment.receipt_no)
        self.assertTrue(body['redirection_url'].endswith('/api/payments/paymob/return/'))
        self.assertNotIn('notification_url', body)
        # Pending money is not paid money.
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'unpaid')

    def test_start_rules(self):
        self.assertEqual(self.start(user=self.billing)[0].status_code, 403)
        other = Invoice.objects.create(patient=self.other, due_date=timezone.localdate())
        self.as_(self.pat_user)
        self.assertEqual(self.client.post(f'/api/invoices/me/{other.pk}/pay-online/').status_code, 404)
        self.invoice.cancel()
        self.assertEqual(self.start()[0].status_code, 400)

    def test_gateway_failure_marks_payment_failed(self):
        self.as_(self.pat_user)
        with mock.patch('apps.billing.paymob._post', side_effect=paymob.PaymobError('Could not reach Paymob.')):
            r = self.client.post(f'/api/invoices/me/{self.invoice.pk}/pay-online/')
        self.assertEqual(r.status_code, 502)
        self.assertEqual(Payment.objects.get().status, 'failed')

    def test_not_configured(self):
        with override_settings(PAYMOB={**PAYMOB, 'SECRET_KEY': ''}):
            self.assertEqual(self.start()[0].status_code, 502)
            self.as_(self.pat_user)
            detail = self.client.get(f'/api/invoices/me/{self.invoice.pk}/')
            self.assertFalse(detail.data['online_payment_available'])

    # ---------------------------------------------------------------- callbacks

    def test_successful_callback_pays_the_invoice_once(self):
        self.start()
        self.assertEqual(self.callback(transaction_obj()).status_code, 200)
        self.assertEqual(self.callback(transaction_obj()).status_code, 200)  # Paymob may retry
        payment = Payment.objects.get()
        self.assertEqual((payment.status, payment.gateway_txn_id), ('succeeded', '9001'))
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'paid')
        self.as_(self.pat_user)
        receipt = self.client.get(f'/api/payments/me/{payment.pk}/receipt/')
        self.assertEqual(receipt.status_code, 200)

    def test_bad_signature_is_rejected(self):
        self.start()
        self.assertEqual(self.callback(transaction_obj(), signature='0' * 128).status_code, 403)
        tampered = transaction_obj()
        signature = paymob.hmac_for_processed(tampered)
        tampered['amount_cents'] = 1
        self.assertEqual(self.callback(tampered, signature=signature).status_code, 403)
        self.assertEqual(Payment.objects.get().status, 'pending')

    def test_declined_then_retried_successfully(self):
        self.start()
        self.callback(transaction_obj(success=False, txn_id=1))
        payment = Payment.objects.get()
        self.assertEqual(payment.status, 'failed')
        self.as_(self.pat_user)
        self.assertEqual(self.client.get(f'/api/payments/me/{payment.pk}/receipt/').status_code, 404)
        self.callback(transaction_obj(success=True, txn_id=2))  # same checkout, second card
        payment.refresh_from_db()
        self.assertEqual((payment.status, payment.gateway_txn_id), ('succeeded', '2'))

    def test_pending_result_keeps_payment_pending(self):
        self.start()
        self.callback(transaction_obj(success=False, pending=True))
        self.assertEqual(Payment.objects.get().status, 'pending')

    def test_unknown_order_falls_back_to_reference(self):
        self.start(intention={**INTENTION, 'intention_order_id': None})
        payment = Payment.objects.get()
        obj = transaction_obj(order_id=777)
        obj['order']['merchant_order_id'] = payment.receipt_no
        self.callback(obj)
        payment.refresh_from_db()
        self.assertEqual((payment.status, payment.gateway_order_id), ('succeeded', '777'))

    def test_non_transaction_callbacks_are_ignored(self):
        self.client.force_authenticate(None)
        r = self.client.post('/api/payments/paymob/callback/', {'type': 'TOKEN', 'obj': {}}, format='json')
        self.assertEqual(r.status_code, 200)

    def test_browser_return_records_and_redirects(self):
        self.start()
        params = {'amount_cents': '100000', 'created_at': '2026-11-24T10:00:00.000000', 'currency': 'EGP',
                  'error_occured': 'false', 'has_parent_transaction': 'false', 'id': '9001',
                  'integration_id': '123', 'is_3d_secure': 'true', 'is_auth': 'false', 'is_capture': 'false',
                  'is_refunded': 'false', 'is_standalone_payment': 'true', 'is_voided': 'false',
                  'order_id': '555', 'owner': '302852', 'pending': 'false', 'source_data_pan': '2346',
                  'source_data_sub_type': 'MasterCard', 'source_data_type': 'card', 'success': 'true'}
        params['hmac'] = paymob.hmac_for_response(params)
        self.client.force_authenticate(None)
        r = self.client.get(f'/api/payments/paymob/return/?{urlencode(params)}')
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r['Location'].endswith(f'/my-invoices/{self.invoice.pk}?payment=succeeded'))
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'paid')

        params['hmac'] = '0' * 128
        r = self.client.get(f'/api/payments/paymob/return/?{urlencode(params)}')
        self.assertTrue(r['Location'].endswith('/my-invoices?payment=unverified'))

    def test_cannot_cancel_while_patient_is_paying(self):
        from django.core.exceptions import ValidationError

        self.start()
        with self.assertRaises(ValidationError):
            self.invoice.cancel()
        Payment.objects.update(paid_at=timezone.now() - datetime.timedelta(hours=1))  # abandoned
        self.invoice.cancel()
        self.assertEqual(self.invoice.status, 'cancelled')

    def test_desk_form_still_rejects_online_method(self):
        self.as_(self.billing)
        r = self.client.post(f'/api/invoices/{self.invoice.pk}/payments/',
                             {'amount': '10.00', 'method': 'online'}, format='json')
        self.assertEqual(r.status_code, 400)
