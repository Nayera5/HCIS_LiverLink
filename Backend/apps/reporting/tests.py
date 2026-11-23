"""Reporting & Analytics tests (module 15): permissions, report numbers, date filters and exports."""
import datetime
from decimal import Decimal

from django.utils import timezone

from apps.accounts.models import AuditLog, User
from apps.billing.models import Invoice, InvoiceItem, Payment, Service
from apps.emr.models import Diagnosis, Encounter
from apps.registry.models import DonorApplication
from apps.registry.test_api import PatientAPITestBase, make_patient
from apps.scheduling.models import Appointment

PATIENTS = '/api/reports/patients/'
FINANCIAL = '/api/reports/financial/'
USAGE = '/api/reports/system-usage/'


def section(report, key):
    return next(s for s in report['sections'] if s['key'] == key)


def summary(report, label):
    return next(item['value'] for item in report['summary'] if item['label'] == label)


class ReportTestBase(PatientAPITestBase):
    def get(self, user, url, **params):
        self.as_(user)
        return self.client.get(url, params)


class PermissionTests(ReportTestBase):
    def test_who_can_open_each_report(self):
        allowed = {
            PATIENTS: {self.root, self.admin, self.coord, self.hep},
            FINANCIAL: {self.root, self.admin, self.billing},
            USAGE: {self.root, self.admin},
        }
        everyone = [self.root, self.admin, self.coord, self.hep, self.rad, self.surg, self.billing,
                    self.nojob, self.pat_user]
        for url, users in allowed.items():
            for user in everyone:
                with self.subTest(url=url, user=user.username):
                    expected = 200 if user in users else 403
                    self.assertEqual(self.get(user, url).status_code, expected)

    def test_anonymous_is_rejected(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(PATIENTS).status_code, 401)


class PeriodValidationTests(ReportTestBase):
    def test_bad_dates_and_export_are_rejected(self):
        self.assertEqual(self.get(self.admin, PATIENTS, date_from='01/02/2026').status_code, 400)
        r = self.get(self.admin, PATIENTS, date_from='2026-03-01', date_to='2026-02-01')
        self.assertEqual(r.status_code, 400)
        self.assertIn('date_to', r.data)
        self.assertEqual(self.get(self.admin, PATIENTS, export='xlsx').status_code, 400)

    def test_period_is_returned(self):
        r = self.get(self.admin, PATIENTS, date_from='2026-01-01')
        self.assertEqual(r.data['period'], {'date_from': '2026-01-01', 'date_to': None})


class PatientReportTests(ReportTestBase):
    def setUp(self):
        super().setUp()
        self.donor = make_patient(first_name='Dina', last_name='Donor', category='donor', phone='0122',
                                  national_id='29501011234567')
        doctor = self.hep.staff_profile
        # `own` has cirrhosis on two visits (counted once); `other` has it once and HCC once.
        for patient, code, description in [(self.own, 'K74.6', 'Cirrhosis'), (self.own, 'K74.6', 'Cirrhosis'),
                                           (self.other, 'K74.6', 'Cirrhosis'), (self.other, 'C22.0', 'HCC')]:
            encounter = Encounter.objects.create(patient=patient, staff=doctor)
            Diagnosis.objects.create(encounter=encounter, icd10_code=code, description=description)
        DonorApplication.objects.create(donor=self.donor, recipient=self.own, relationship='sibling')

    def test_counts(self):
        r = self.get(self.coord, PATIENTS)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(section(r.data, 'by_diagnosis')['rows'],
                         [['K74.6', 'Cirrhosis', 2], ['C22.0', 'HCC', 1]])
        self.assertEqual(section(r.data, 'by_category')['rows'],
                         [['Liver patient', 2], ['Transplant recipient', 0], ['Living donor', 1]])
        self.assertIn(['Submitted', 1], section(r.data, 'applications_by_status')['rows'])
        self.assertEqual(summary(r.data, 'Patients registered'), 3)
        self.assertEqual(summary(r.data, 'Patients with a diagnosis'), 2)

    def test_date_filter(self):
        old = timezone.now() - datetime.timedelta(days=400)
        Diagnosis.objects.filter(icd10_code='C22.0').update(diagnosed_at=old)
        since = (timezone.localdate() - datetime.timedelta(days=30)).isoformat()
        r = self.get(self.hep, PATIENTS, date_from=since)
        codes = [row[0] for row in section(r.data, 'by_diagnosis')['rows']]
        self.assertEqual(codes, ['K74.6'])


class FinancialReportTests(ReportTestBase):
    def setUp(self):
        super().setUp()
        self.consult = Service.objects.create(code='RPT-CONS', name='Report consultation',
                                              category='consultation', price=Decimal('300'))
        self.ct = Service.objects.create(code='RPT-CT', name='Report CT', category='imaging',
                                         price=Decimal('1000'))
        today = timezone.localdate()
        self.paid = self.invoice([(self.consult, 1)], today)
        Payment.objects.create(invoice=self.paid, amount=Decimal('300'), method='cash')
        self.partial = self.invoice([(self.ct, 1), (self.consult, 1)], today)
        Payment.objects.create(invoice=self.partial, amount=Decimal('500'), method='card')
        cancelled = self.invoice([(self.ct, 2)], today)
        cancelled.cancel()

    def invoice(self, lines, issue_date):
        invoice = Invoice.objects.create(patient=self.own, issue_date=issue_date,
                                         due_date=issue_date + datetime.timedelta(days=14))
        for service, quantity in lines:
            InvoiceItem.objects.create(invoice=invoice, service=service, quantity=quantity)
        invoice.recompute_total()
        return invoice

    def test_revenue_and_unpaid(self):
        r = self.get(self.billing, FINANCIAL)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(summary(r.data, 'Collected (EGP)'), '800.00')
        self.assertEqual(summary(r.data, 'Billed (EGP)'), '1600.00')     # cancelled invoice excluded
        self.assertEqual(summary(r.data, 'Outstanding balance (EGP)'), '800.00')
        self.assertEqual(section(r.data, 'revenue_by_service')['rows'],
                         [['Report CT', 'RPT-CT', 1, '1000.00'], ['Report consultation', 'RPT-CONS', 2, '600.00']])
        month = timezone.localdate().strftime('%Y-%m')
        self.assertEqual(section(r.data, 'revenue_by_month')['rows'], [[month, 2, '800.00']])
        unpaid = section(r.data, 'unpaid_invoices')['rows']
        self.assertEqual([row[0] for row in unpaid], [self.partial.invoice_no])
        self.assertEqual(unpaid[0][-1], '800.00')

    def test_refunded_payments_are_not_revenue(self):
        Payment.objects.filter(invoice=self.paid).update(status=Payment.Status.REFUNDED)
        r = self.get(self.billing, FINANCIAL)
        self.assertEqual(summary(r.data, 'Collected (EGP)'), '500.00')


class SystemUsageReportTests(ReportTestBase):
    def setUp(self):
        super().setUp()
        now = timezone.now()
        User.objects.filter(pk__in=[self.hep.pk, self.pat_user.pk]).update(last_login=now)
        start = now - datetime.timedelta(days=1)
        for status in ('completed', 'completed', 'completed', 'no_show', 'cancelled'):
            Appointment.objects.create(patient=self.own, staff=self.hep.staff_profile, booked_by=self.coord,
                                       appointment_type='consultation', start_time=start,
                                       end_time=start + datetime.timedelta(minutes=30), status=status)
            start += datetime.timedelta(minutes=30)

    def test_usage_numbers(self):
        r = self.get(self.admin, USAGE)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(summary(r.data, 'Signed-in users'), 2)
        self.assertEqual(summary(r.data, 'Appointments'), 5)
        self.assertEqual(summary(r.data, 'No-show rate'), '25.0%')         # 1 / (3 completed + 1)
        roles = dict(section(r.data, 'signed_in_by_role')['rows'])
        self.assertEqual((roles['Clinical staff'], roles['Patient']), (1, 1))

    def test_no_show_rate_without_appointments(self):
        Appointment.objects.all().delete()
        self.assertEqual(summary(self.get(self.admin, USAGE).data, 'No-show rate'), '—')


class ExportTests(ReportTestBase):
    def test_csv_export_is_audited(self):
        r = self.get(self.billing, FINANCIAL, export='csv')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r['Content-Type'].startswith('text/csv'))
        self.assertIn('attachment; filename="liverlink-financial-', r['Content-Disposition'])
        text = r.content.decode('utf-8-sig')
        self.assertIn('Financial report', text)
        self.assertIn('Unpaid invoices', text)
        entry = AuditLog.objects.get(action='export')
        self.assertEqual((entry.user, entry.entity_type), (self.billing, 'reporting.financial'))

    def test_pdf_export(self):
        for url in (PATIENTS, FINANCIAL, USAGE):
            with self.subTest(url=url):
                r = self.get(self.admin, url, export='pdf')
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r['Content-Type'], 'application/pdf')
                self.assertTrue(b''.join(r.streaming_content).startswith(b'%PDF'))

    def test_viewing_is_not_audited_and_export_needs_permission(self):
        self.get(self.admin, PATIENTS)
        self.assertFalse(AuditLog.objects.filter(action='export').exists())
        self.assertEqual(self.get(self.rad, PATIENTS, export='csv').status_code, 403)
