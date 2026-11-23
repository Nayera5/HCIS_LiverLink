"""
Report builders for Reporting & Analytics (spec §15). Each builder reads existing data (no
tables of its own) and returns one report in a single shape, used by the API, the CSV/PDF
exports and the frontend charts:

    {
        'key': 'financial',
        'title': 'Financial report',
        'period': {'date_from': '2026-01-01' | None, 'date_to': ... | None},
        'summary': [{'label': 'Collected', 'value': '1500.00'}, ...],
        'sections': [{
            'key': 'revenue_by_month',
            'title': 'Revenue by month (collected)',
            'columns': ['Month', 'Payments', 'Collected (EGP)'],
            'rows': [['2026-01', 3, '1500.00'], ...],
            'chart_column': 2,      # index of the numeric column to chart (label = column 0), or None
        }, ...],
    }

Money values are decimal strings ('1500.00'), the same as the billing API.
The date filter is inclusive on both ends; with no dates the report covers all time.
"""
import datetime
from decimal import Decimal

from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.billing.models import Invoice, InvoiceItem, Payment
from apps.emr.models import Diagnosis
from apps.registry.models import DonorApplication, Patient
from apps.scheduling.models import Appointment

ZERO = Value(Decimal('0'), output_field=DecimalField(max_digits=12, decimal_places=2))


# --------------------------------------------------------------------------- helpers

def parse_period(params):
    """Read `date_from` / `date_to` (YYYY-MM-DD, optional) from query params."""
    period = {}
    errors = {}
    for key in ('date_from', 'date_to'):
        text = (params.get(key) or '').strip()
        if not text:
            period[key] = None
            continue
        try:
            period[key] = datetime.date.fromisoformat(text)
        except ValueError:
            errors[key] = 'Use the format YYYY-MM-DD.'
    if errors:
        raise ValidationError(errors)
    if period['date_from'] and period['date_to'] and period['date_from'] > period['date_to']:
        raise ValidationError({'date_to': 'The end date cannot be before the start date.'})
    return period['date_from'], period['date_to']


def in_period(queryset, lookup, date_from, date_to):
    """
    Filter `queryset` to the period. `lookup` must compare dates: a DateField ('issue_date') or
    a DateTimeField with `__date` ('paid_at__date').
    """
    if date_from:
        queryset = queryset.filter(**{f'{lookup}__gte': date_from})
    if date_to:
        queryset = queryset.filter(**{f'{lookup}__lte': date_to})
    return queryset


def money(value):
    return str((value or Decimal('0')).quantize(Decimal('0.01')))


def month_label(value):
    return value.strftime('%Y-%m') if value else '—'


def _report(key, title, date_from, date_to, summary, sections):
    return {
        'key': key,
        'title': title,
        'period': {
            'date_from': date_from.isoformat() if date_from else None,
            'date_to': date_to.isoformat() if date_to else None,
        },
        'summary': [{'label': label, 'value': value} for label, value in summary],
        'sections': sections,
    }


def _section(key, title, columns, rows, chart_column=None):
    return {'key': key, 'title': title, 'columns': columns, 'rows': rows, 'chart_column': chart_column}


def _choice_counts(queryset, field, choices):
    """[[label, count], ...] for every choice, including zero counts, in the choices' order."""
    counts = dict(queryset.values_list(field).annotate(n=Count('pk')).values_list(field, 'n'))
    return [[label, counts.get(value, 0)] for value, label in choices]


# --------------------------------------------------------------------------- patient & donor statistics

def patient_report(date_from=None, date_to=None):
    """
    Patients by diagnosis (ICD-10), patients by category, donor applications by status.
    Period: patient registration date, diagnosis date, application submission date.
    """
    patients = in_period(Patient.objects.all(), 'created_at__date', date_from, date_to)
    diagnoses = in_period(Diagnosis.objects.all(), 'diagnosed_at__date', date_from, date_to)
    applications = in_period(DonorApplication.objects.all(), 'submitted_at__date', date_from, date_to)

    # A patient with the same code on several visits is counted once for that code.
    by_diagnosis = (diagnoses.values('icd10_code')
                    .annotate(patients=Count('patient', distinct=True))
                    .order_by('-patients', 'icd10_code'))
    descriptions = {}
    for code, description in diagnoses.order_by('-diagnosed_at').values_list('icd10_code', 'description'):
        descriptions.setdefault(code, description)  # most recent wording of each code
    diagnosis_rows = [[row['icd10_code'], descriptions.get(row['icd10_code'], ''), row['patients']]
                      for row in by_diagnosis]

    category_rows = _choice_counts(patients, 'category', Patient.Category.choices)
    application_rows = _choice_counts(applications, 'status', DonorApplication.Status.choices)

    summary = [
        ('Patients registered', patients.count()),
        ('Living donors registered', patients.filter(category=Patient.Category.DONOR).count()),
        ('Patients with a diagnosis', diagnoses.values('patient').distinct().count()),
        ('Donor applications', applications.count()),
    ]
    sections = [
        _section('by_diagnosis', 'Patients by diagnosis (ICD-10)',
                 ['ICD-10 code', 'Description', 'Patients'], diagnosis_rows, chart_column=2),
        _section('by_category', 'Patients by category', ['Category', 'Patients'], category_rows, chart_column=1),
        _section('applications_by_status', 'Donor applications by status',
                 ['Status', 'Applications'], application_rows, chart_column=1),
    ]
    return _report('patients', 'Patient & donor statistics', date_from, date_to, summary, sections)


# --------------------------------------------------------------------------- financial

def financial_report(date_from=None, date_to=None):
    """
    Revenue by month (successful payments, by payment date), revenue by service (billed amounts
    on non-cancelled invoices, by issue date) and the list of unpaid / partly paid invoices.
    """
    payments = in_period(Payment.objects.filter(status=Payment.Status.SUCCEEDED), 'paid_at__date', date_from, date_to)
    items = in_period(InvoiceItem.objects.exclude(invoice__status=Invoice.Status.CANCELLED),
                      'invoice__issue_date', date_from, date_to)
    open_invoices = in_period(Invoice.objects.filter(status__in=Invoice.OPEN_STATUSES),
                              'issue_date', date_from, date_to)

    by_month = (payments.annotate(month=TruncMonth('paid_at')).values('month')
                .annotate(count=Count('pk'), total=Sum('amount')).order_by('month'))
    month_rows = [[month_label(row['month']), row['count'], money(row['total'])] for row in by_month]

    by_service = (items.values('service__code', 'service__name')
                  .annotate(quantity=Sum('quantity'), total=Sum('line_total'))
                  .order_by('-total', 'service__name'))
    service_rows = [[row['service__name'], row['service__code'], row['quantity'], money(row['total'])]
                    for row in by_service]

    open_invoices = (open_invoices.select_related('patient')
                     .annotate(paid=Coalesce(Sum('payments__amount',
                                                 filter=Q(payments__status=Payment.Status.SUCCEEDED)), ZERO))
                     .order_by('due_date', 'invoice_no'))
    unpaid_rows = []
    outstanding = Decimal('0')
    for invoice in open_invoices:
        balance = invoice.total_amount - invoice.paid
        outstanding += balance
        unpaid_rows.append([
            invoice.invoice_no, invoice.patient.full_name, invoice.patient.mrn,
            invoice.issue_date.isoformat(), invoice.due_date.isoformat(),
            invoice.get_status_display(), money(invoice.total_amount), money(invoice.paid), money(balance),
        ])

    summary = [
        ('Collected (EGP)', money(payments.aggregate(total=Sum('amount'))['total'])),
        ('Billed (EGP)', money(items.aggregate(total=Sum('line_total'))['total'])),
        ('Outstanding balance (EGP)', money(outstanding)),
        ('Unpaid invoices', len(unpaid_rows)),
    ]
    sections = [
        _section('revenue_by_month', 'Revenue by month (collected)',
                 ['Month', 'Payments', 'Collected (EGP)'], month_rows, chart_column=2),
        _section('revenue_by_service', 'Revenue by service (billed)',
                 ['Service', 'Code', 'Quantity', 'Billed (EGP)'], service_rows, chart_column=3),
        _section('unpaid_invoices', 'Unpaid invoices',
                 ['Invoice', 'Patient', 'MRN', 'Issued', 'Due', 'Status', 'Total (EGP)', 'Paid (EGP)',
                  'Balance (EGP)'], unpaid_rows),
    ]
    return _report('financial', 'Financial report', date_from, date_to, summary, sections)


# --------------------------------------------------------------------------- system usage

def system_usage_report(date_from=None, date_to=None):
    """
    Signed-in users (User.last_login inside the period, by role), new accounts by month and
    appointments by status with the no-show rate.

    LiverLink stores only each user's *last* sign-in (SIMPLE_JWT UPDATE_LAST_LOGIN), not every
    login, so "signed-in users" counts users whose most recent sign-in falls in the period.
    No-show rate = no-shows / (completed + no-shows), by appointment start time.
    """
    signed_in = in_period(User.objects.filter(last_login__isnull=False), 'last_login__date', date_from, date_to)
    new_accounts = in_period(User.objects.all(), 'date_joined__date', date_from, date_to)
    appointments = in_period(Appointment.objects.all(), 'start_time__date', date_from, date_to)

    by_month = (new_accounts.annotate(month=TruncMonth('date_joined')).values('month')
                .annotate(count=Count('pk')).order_by('month'))
    month_rows = [[month_label(row['month']), row['count']] for row in by_month]

    status_rows = _choice_counts(appointments, 'status', Appointment.Status.choices)
    counts = dict(appointments.values_list('status').annotate(n=Count('pk')).values_list('status', 'n'))
    no_shows = counts.get(Appointment.Status.NO_SHOW, 0)
    attended_or_missed = no_shows + counts.get(Appointment.Status.COMPLETED, 0)
    no_show_rate = f'{no_shows / attended_or_missed * 100:.1f}%' if attended_or_missed else '—'

    summary = [
        ('Active accounts', User.objects.filter(is_active=True).count()),
        ('Signed-in users', signed_in.count()),
        ('New accounts', new_accounts.count()),
        ('Appointments', appointments.count()),
        ('No-show rate', no_show_rate),
    ]
    sections = [
        _section('signed_in_by_role', 'Signed-in users by role', ['Role', 'Users'],
                 _choice_counts(signed_in, 'role', User.Role.choices), chart_column=1),
        _section('new_accounts_by_month', 'New accounts by month', ['Month', 'Accounts'],
                 month_rows, chart_column=1),
        _section('appointments_by_status', 'Appointments by status', ['Status', 'Appointments'],
                 status_rows, chart_column=1),
    ]
    return _report('system_usage', 'System usage report', date_from, date_to, summary, sections)
