"""
Automatic invoice generation (spec §13 "Invoice Generation": invoices are created from completed
appointments and tests).

- invoice_for_appointment(): called when an appointment is marked completed. The visit fee comes
  from APPOINTMENT_SERVICE_CODES. Lab visits carry no fee: their tests are billed with the order.
- invoice_for_lab_order(): called when every test of a lab order has a result. Each test is billed
  with the active 'lab' service whose LOINC standard_code equals the test's code.

Both are idempotent (a source already on a non-cancelled invoice is not billed again) and never
break the clinical action that triggered them: a billing problem (e.g. a service missing from
the catalog) is logged and the appointment / result is still saved. Billing staff can then add
the charge by hand. Automatic invoices have no `issued_by` (spec §4.39).
"""
import datetime
import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import Invoice, InvoiceItem, Service

logger = logging.getLogger(__name__)

DUE_AFTER_DAYS = 14

# Appointment.appointment_type -> Service.code (seeded by migration 0004).
APPOINTMENT_SERVICE_CODES = {
    'consultation': 'CONS-001',          # Hepatology consultation
    'ct_scan': 'IMG-003',                # Abdominal CT with contrast
    'donor_evaluation': 'CONS-005',
    'recipient_evaluation': 'CONS-002',
    'follow_up': 'CONS-003',             # Post-transplant follow-up
    # 'lab_visit': no visit fee, the tests are billed when the lab order is resulted.
}
SURGEON_CONSULTATION_CODE = 'CONS-004'   # consultation with a transplant surgeon


def _service_code_for(appointment):
    if appointment.appointment_type == 'consultation' and appointment.staff.job_title == 'transplant_surgeon':
        return SURGEON_CONSULTATION_CODE
    return APPOINTMENT_SERVICE_CODES.get(appointment.appointment_type)


def _already_billed(**source):
    return InvoiceItem.objects.filter(**source).exclude(invoice__status=Invoice.Status.CANCELLED).exists()


def _create_invoice(patient, lines):
    """lines: [(service, quantity, {'appointment': ..., 'lab_order': ...}), ...]. Prices are copied now."""
    today = timezone.localdate()
    invoice = Invoice.objects.create(patient=patient, issued_by=None, issue_date=today,
                                     due_date=today + datetime.timedelta(days=DUE_AFTER_DAYS))
    total = Decimal('0')
    for service, quantity, source in lines:
        item = InvoiceItem.objects.create(invoice=invoice, service=service, quantity=quantity,
                                          unit_price=service.price, **source)
        total += item.line_total
    invoice.total_amount = total
    invoice.save(update_fields=['total_amount', 'updated_at'])
    return invoice


def _safely(label, build):
    """Run `build` in a savepoint; on any error log it and return None instead of failing the caller."""
    try:
        with transaction.atomic():
            return build()
    except Exception:
        logger.exception('Automatic invoice for %s failed; add the charge manually.', label)
        return None


def invoice_for_appointment(appointment):
    """Invoice the visit fee of a completed appointment. Returns the invoice, or None if nothing was billed."""
    if appointment.status != 'completed' or _already_billed(appointment=appointment):
        return None
    code = _service_code_for(appointment)
    if code is None:
        return None
    service = Service.objects.filter(code=code, is_active=True).first()
    if service is None:
        logger.warning('No active service %s for appointment #%s; it was not billed.', code, appointment.pk)
        return None
    return _safely(f'appointment #{appointment.pk}', lambda: _create_invoice(
        appointment.patient, [(service, 1, {'appointment': appointment})]))


def invoice_for_lab_order(order):
    """Invoice the tests of a fully resulted lab order. Returns the invoice, or None if nothing was billed."""
    if order.status != 'resulted' or _already_billed(lab_order=order):
        return None
    codes = list(order.results.values_list('lab_test__code', flat=True))
    services = {service.standard_code: service for service in Service.objects.filter(
        category=Service.Category.LAB, coding_system=Service.CodingSystem.LOINC,
        standard_code__in=codes, is_active=True)}
    missing = sorted(set(codes) - set(services))
    if missing:
        logger.warning('Lab order #%s: no active lab service for LOINC %s; those tests were not billed.',
                       order.pk, ', '.join(missing))
    lines = [(services[code], 1, {'lab_order': order}) for code in codes if code in services]
    if not lines:
        return None
    return _safely(f'lab order #{order.pk}', lambda: _create_invoice(order.patient, lines))
