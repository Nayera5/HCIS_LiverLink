"""Automatic invoices (completed appointments, resulted lab orders) and payment locking."""
import datetime
from decimal import Decimal
from unittest import mock

from django.utils import timezone

from apps.labs import services as lab_services
from apps.labs.models import LabTest
from apps.registry.test_api import PatientAPITestBase
from apps.scheduling.models import Appointment

from .models import Invoice, InvoiceItem, Payment, Service
from .serializers import PaymentCreateSerializer


class AppointmentInvoiceTests(PatientAPITestBase):
    def appointment(self, appointment_type='consultation', staff=None, status=Appointment.Status.CHECKED_IN):
        start = timezone.now() - datetime.timedelta(hours=1)
        return Appointment.objects.create(
            patient=self.own, staff=(staff or self.hep).staff_profile, booked_by=self.coord,
            appointment_type=appointment_type, start_time=start,
            end_time=start + datetime.timedelta(minutes=30), status=status)

    def complete(self, appointment, user=None):
        self.as_(user or self.coord)
        return self.client.post(f'/api/scheduling/appointments/{appointment.pk}/complete/')

    def test_completing_an_appointment_creates_an_invoice(self):
        appointment = self.appointment()
        self.assertEqual(self.complete(appointment).status_code, 200)
        item = InvoiceItem.objects.get(appointment=appointment)
        service = Service.objects.get(code='CONS-001')
        self.assertEqual((item.service, item.quantity, item.unit_price), (service, 1, service.price))
        invoice = item.invoice
        self.assertEqual((invoice.patient, invoice.issued_by, invoice.status), (self.own, None, 'unpaid'))
        self.assertEqual(invoice.total_amount, service.price)
        self.assertEqual(invoice.due_date - invoice.issue_date, datetime.timedelta(days=14))

    def test_surgeon_consultation_uses_the_surgeon_fee(self):
        appointment = self.appointment(staff=self.surg)
        self.complete(appointment)
        self.assertEqual(InvoiceItem.objects.get(appointment=appointment).service.code, 'CONS-004')

    def test_lab_visit_has_no_visit_fee(self):
        appointment = self.appointment('lab_visit')
        self.assertEqual(self.complete(appointment).status_code, 200)
        self.assertFalse(InvoiceItem.objects.filter(appointment=appointment).exists())

    def test_not_billed_twice_and_rebilled_after_cancellation(self):
        from .services import invoice_for_appointment

        appointment = self.appointment()
        self.complete(appointment)
        appointment.refresh_from_db()
        self.assertIsNone(invoice_for_appointment(appointment))
        InvoiceItem.objects.get(appointment=appointment).invoice.cancel()
        self.assertIsNotNone(invoice_for_appointment(appointment))
        self.assertEqual(InvoiceItem.objects.filter(appointment=appointment).count(), 2)

    def test_inactive_service_does_not_block_completion(self):
        Service.objects.filter(code='CONS-001').update(is_active=False)
        appointment = self.appointment()
        self.assertEqual(self.complete(appointment).status_code, 200)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'completed')
        self.assertFalse(InvoiceItem.objects.filter(appointment=appointment).exists())

    def test_billing_error_does_not_block_completion(self):
        appointment = self.appointment()
        with mock.patch('apps.billing.services._create_invoice', side_effect=RuntimeError('boom')), \
                self.assertLogs('apps.billing.services', 'ERROR'):
            self.assertEqual(self.complete(appointment).status_code, 200)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'completed')

    def test_manual_invoice_appointment_must_belong_to_patient(self):
        appointment = self.appointment(status=Appointment.Status.COMPLETED)
        service = Service.objects.get(code='CONS-001')
        self.as_(self.billing)
        payload = {'patient': self.other.pk, 'due_date': timezone.localdate().isoformat(),
                   'items': [{'service': service.pk, 'appointment': appointment.pk}]}
        self.assertEqual(self.client.post('/api/invoices/', payload, format='json').status_code, 400)
        payload['patient'] = self.own.pk
        r = self.client.post('/api/invoices/', payload, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['items'][0]['appointment'], appointment.pk)


class LabOrderInvoiceTests(PatientAPITestBase):
    def setUp(self):
        super().setUp()
        self.bili = LabTest.objects.create(code='1975-2', name='Bilirubin', normal_min=Decimal('0.1'),
                                           normal_max=Decimal('1.2'))
        self.alt = LabTest.objects.create(code='1742-6', name='ALT', normal_min=7, normal_max=56)
        self.order = lab_services.create_order(self.own, self.hep.staff_profile, [self.bili, self.alt])

    def enter(self, test, value):
        lab_services.record_result(self.order.results.get(lab_test=test), Decimal(value))
        self.order.refresh_from_db()

    def test_invoice_only_once_all_results_are_in(self):
        self.enter(self.bili, '0.8')
        self.assertFalse(InvoiceItem.objects.filter(lab_order=self.order).exists())
        self.enter(self.alt, '30')
        items = InvoiceItem.objects.filter(lab_order=self.order).select_related('service', 'invoice')
        self.assertEqual(sorted(item.service.code for item in items), ['LAB-001', 'LAB-003'])
        invoice = items[0].invoice
        self.assertEqual(invoice.total_amount, sum(item.line_total for item in items))
        self.assertEqual(invoice.patient, self.own)

    def test_test_without_a_lab_service_is_skipped(self):
        Service.objects.filter(code='LAB-003').update(is_active=False)  # bilirubin
        self.enter(self.bili, '0.8')
        with self.assertLogs('apps.billing.services', 'WARNING'):
            self.enter(self.alt, '30')
        self.assertEqual([i.service.code for i in InvoiceItem.objects.filter(lab_order=self.order)], ['LAB-001'])

    def test_not_billed_twice(self):
        from .services import invoice_for_lab_order

        self.enter(self.bili, '0.8')
        self.enter(self.alt, '30')
        self.assertIsNone(invoice_for_lab_order(self.order))
        self.assertEqual(Invoice.objects.filter(items__lab_order=self.order).distinct().count(), 1)


class PaymentLockTests(PatientAPITestBase):
    def setUp(self):
        super().setUp()
        service = Service.objects.get(code='CONS-001')
        self.invoice = Invoice.objects.create(patient=self.own, due_date=timezone.localdate())
        InvoiceItem.objects.create(invoice=self.invoice, service=service, quantity=1)
        self.invoice.recompute_total()

    def pay(self, invoice, amount):
        serializer = PaymentCreateSerializer(data={'amount': amount, 'method': 'cash'}, context={'invoice': invoice})
        serializer.is_valid(raise_exception=True)
        return serializer.save()

    def test_payment_locks_the_invoice_row(self):
        with mock.patch('django.db.models.query.QuerySet.select_for_update',
                        autospec=True, side_effect=lambda qs, *a, **k: qs) as lock:
            self.pay(self.invoice, '100.00')
        self.assertTrue(any(call.args[0].model is Invoice for call in lock.call_args_list))

    def test_stale_invoice_cannot_be_overpaid(self):
        """Two requests that both loaded the invoice before either paid: the second sees the first."""
        stale = Invoice.objects.get(pk=self.invoice.pk)
        total = str(self.invoice.total_amount)
        self.pay(self.invoice, total)
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.pay(stale, total)
        self.assertEqual(Payment.objects.filter(invoice=self.invoice).count(), 1)

    def test_cancel_checks_payments_on_the_locked_row(self):
        stale = Invoice.objects.get(pk=self.invoice.pk)
        self.pay(self.invoice, '100.00')
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            stale.cancel()
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'partially_paid')
