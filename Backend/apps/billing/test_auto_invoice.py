"""Automatic invoices (completed appointments) and payment locking."""
import datetime
from decimal import Decimal
from unittest import mock

from django.utils import timezone

from apps.labs import services as lab_services
from apps.labs.models import LabTest
from apps.radiology.models import ImagingOrder
from apps.registry.test_api import PatientAPITestBase
from apps.scheduling.models import Appointment
from apps.scheduling.serializers import APPOINTMENT_DOCTOR_TITLES

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

    def test_every_bookable_visit_type_is_billed_with_its_own_service(self):
        expected = {
            'hepatology_consultation': ('CONS-001', 'Hepatology Consultation', 1000),
            'transplant_consultation': ('CONS-003', 'Transplant Surgery Consultation', 1200),
            'follow_up': ('CONS-002', 'Post-Transplant Follow-up', 800),
            'recipient_evaluation': ('EVA-001', 'Recipient Evaluation Visit', 1500),
            'donor_evaluation': ('EVA-002', 'Donor Evaluation Visit', 1000),
            'examination': ('EXM-001', 'Clinical Examination', 600),
        }
        self.assertEqual(set(expected), set(APPOINTMENT_DOCTOR_TITLES))  # every bookable type is covered
        for visit_type, (code, name, price) in expected.items():
            with self.subTest(visit_type):
                appointment = self.appointment(visit_type)
                self.assertEqual(self.complete(appointment).status_code, 200)
                item = InvoiceItem.objects.get(appointment=appointment)
                self.assertEqual((item.service.code, item.service.name, item.unit_price), (code, name, price))

    def test_invoice_appears_in_the_patient_portal(self):
        appointment = self.appointment('examination')
        self.complete(appointment)
        self.as_(self.pat_user)
        invoices = self.client.get('/api/invoices/me/').data['invoices']
        self.assertEqual([i['id'] for i in invoices],
                         [InvoiceItem.objects.get(appointment=appointment).invoice_id])

    def test_visit_that_was_not_completed_is_not_billed(self):
        for visit_status, action in (('checked_in', 'cancel'), ('booked', 'no-show'), ('booked', 'check-in')):
            appointment = self.appointment('examination', status=visit_status)
            self.as_(self.coord)
            self.assertEqual(
                self.client.post(f'/api/scheduling/appointments/{appointment.pk}/{action}/').status_code, 200)
        self.assertFalse(Invoice.objects.exists())

    def test_old_surgeon_consultation_uses_the_surgeon_fee(self):
        appointment = self.appointment(staff=self.surg)
        self.complete(appointment)
        self.assertEqual(InvoiceItem.objects.get(appointment=appointment).service.code, 'CONS-003')

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

    def test_manual_invoice_can_link_acquired_imaging_order(self):
        service = Service.objects.get(code='IMG-003')
        order = ImagingOrder.objects.create(
            patient=self.own, ordered_by=self.hep.staff_profile,
            clinical_indication='Follow-up scan', billing_service=service,
            status=ImagingOrder.Status.ACQUIRED,
        )
        self.as_(self.billing)
        payload = {'patient': self.own.pk, 'due_date': timezone.localdate().isoformat(),
                   'items': [{'service': Service.objects.get(code='IMG-004').pk,
                              'imaging_order': order.pk}]}
        self.assertEqual(self.client.post('/api/invoices/', payload, format='json').status_code, 400)
        payload['items'][0]['service'] = service.pk
        response = self.client.post('/api/invoices/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        item = InvoiceItem.objects.get(imaging_order=order)
        self.assertEqual((item.service, item.unit_price), (service, service.price))

    def test_manual_invoice_rejects_unacquired_or_foreign_imaging_order(self):
        service = Service.objects.get(code='IMG-003')
        order = ImagingOrder.objects.create(
            patient=self.own, ordered_by=self.hep.staff_profile,
            clinical_indication='Follow-up scan', billing_service=service,
        )
        self.as_(self.billing)
        payload = {'patient': self.own.pk, 'due_date': timezone.localdate().isoformat(),
                   'items': [{'service': service.pk, 'imaging_order': order.pk}]}
        self.assertEqual(self.client.post('/api/invoices/', payload, format='json').status_code, 400)
        payload['patient'] = self.other.pk
        order.status = ImagingOrder.Status.ACQUIRED
        order.save(update_fields=['status'])
        self.assertEqual(self.client.post('/api/invoices/', payload, format='json').status_code, 400)


class ImagingOrderInvoiceTests(PatientAPITestBase):
    def setUp(self):
        super().setUp()
        self.service = Service.objects.get(code='IMG-003')
        self.order = ImagingOrder.objects.create(
            patient=self.own, ordered_by=self.hep.staff_profile,
            clinical_indication='Follow-up scan', billing_service=self.service,
            status=ImagingOrder.Status.ACQUIRED,
        )

    def test_billing_operation_locks_order_and_is_idempotent(self):
        from .services import invoice_for_imaging_order

        with mock.patch('django.db.models.query.QuerySet.select_for_update',
                        autospec=True, side_effect=lambda qs, *a, **k: qs) as lock:
            invoice = invoice_for_imaging_order(self.order)
            self.assertTrue(any(call.args[0].model is ImagingOrder for call in lock.call_args_list))
        self.assertIsNotNone(invoice)
        self.assertIsNone(invoice_for_imaging_order(self.order))
        self.assertEqual(InvoiceItem.objects.filter(imaging_order=self.order).count(), 1)

    def test_cancelled_invoice_releases_unique_charge_for_rebilling(self):
        from .services import invoice_for_imaging_order

        first_invoice = invoice_for_imaging_order(self.order)
        first_item = InvoiceItem.objects.get(imaging_order=self.order)
        self.assertTrue(first_item.is_current_imaging_charge)
        first_invoice.cancel()
        first_item.refresh_from_db()
        self.assertFalse(first_item.is_current_imaging_charge)

        self.assertIsNotNone(invoice_for_imaging_order(self.order))
        self.assertIsNone(invoice_for_imaging_order(self.order))
        self.assertEqual(InvoiceItem.objects.filter(imaging_order=self.order).count(), 2)
        self.assertEqual(InvoiceItem.objects.filter(
            imaging_order=self.order, is_current_imaging_charge=True,
        ).count(), 1)

    def test_manual_invoice_cannot_duplicate_active_imaging_charge(self):
        from .services import invoice_for_imaging_order

        invoice_for_imaging_order(self.order)
        self.as_(self.billing)
        payload = {'patient': self.own.pk, 'due_date': timezone.localdate().isoformat(),
                   'items': [{'service': self.service.pk, 'imaging_order': self.order.pk}]}
        response = self.client.post('/api/invoices/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(InvoiceItem.objects.filter(imaging_order=self.order).count(), 1)


class LabOrderNotInvoicedTests(PatientAPITestBase):
    def setUp(self):
        super().setUp()
        self.bili = LabTest.objects.create(code='1975-2', name='Bilirubin', normal_min=Decimal('0.1'),
                                           normal_max=Decimal('1.2'))
        self.alt = LabTest.objects.create(code='1742-6', name='ALT', normal_min=7, normal_max=56)
        self.order = lab_services.create_order(self.own, self.hep.staff_profile, [self.bili, self.alt])

    def enter(self, test, value):
        lab_services.record_result(self.order.results.get(lab_test=test), Decimal(value))
        self.order.refresh_from_db()

    def test_lab_results_do_not_create_an_invoice(self):
        self.enter(self.bili, '0.8')
        self.enter(self.alt, '30')
        self.assertFalse(Invoice.objects.filter(patient=self.own).exists())


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
