"""
Automatic invoice generation (spec §13 "Invoice Generation": invoices are created from completed
appointments and transplant surgeries).

- invoice_for_appointment(): called when an appointment is marked completed. The visit fee comes
  from APPOINTMENT_SERVICE_CODES. Lab visits carry no fee: their tests are billed with the order.
- invoice_for_imaging_order(): called when a scan is acquired and uses the order's explicitly
  selected active imaging service.
  from APPOINTMENT_SERVICE_CODES. Lab visits carry no visit fee.
- invoice_for_surgery(): called when a transplant surgery is marked completed.

Both are idempotent (a source already on a non-cancelled invoice is not billed again) and never
break the clinical action that triggered them: a billing problem (e.g. a service missing from
the catalog) is logged and the clinical action is still saved. Billing staff can then add
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

# Appointment.appointment_type -> Service.code (seeded by migration 0011).
APPOINTMENT_SERVICE_CODES = {
    'hepatology_consultation': 'CONS-001',
    'transplant_consultation': 'CONS-003',
    'follow_up': 'CONS-002',
    'recipient_evaluation': 'EVA-001',
    'donor_evaluation': 'EVA-002',
    'examination': 'EXM-001',
    # Older appointments only; these types can no longer be booked.
    'consultation': 'CONS-001',          # with a transplant surgeon: see _service_code_for()
    'ct_scan': 'IMG-003',
    # 'lab_visit': no visit fee.
}


def _service_code_for(appointment):
    visit_type = appointment.appointment_type
    if visit_type == 'consultation' and appointment.staff.job_title == 'transplant_surgeon':
        visit_type = 'transplant_consultation'
    return APPOINTMENT_SERVICE_CODES.get(visit_type)


def _already_billed(**source):
    return InvoiceItem.objects.filter(**source).exclude(invoice__status=Invoice.Status.CANCELLED).exists()


def _create_invoice(patient, lines):
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


def invoice_for_surgery(surgery):
    """Invoice a completed transplant surgery once. Returns the invoice, or None if not billed."""
    if surgery.status != 'completed' or _already_billed(surgery=surgery):
        return None
    service = Service.objects.filter(
        code='SUR-001', category=Service.Category.SURGERY, is_active=True,
    ).first()
    if service is None:
        logger.warning('No active transplant surgery service SUR-001 for surgery #%s; it was not billed.',
                       surgery.pk)
        return None
    return _safely(f'surgery #{surgery.pk}', lambda: _create_invoice(
        surgery.case.recipient, [(service, 1, {'surgery': surgery})]))

@transaction.atomic
def invoice_for_imaging_order(order, appointment=None):
    """Invoice an acquired scan with its selected catalog service, or log an unmapped scan."""
    from apps.radiology.models import ImagingOrder

    order = ImagingOrder.objects.select_for_update().select_related(
        'patient', 'billing_service',
    ).get(pk=order.pk)
    if order.status != ImagingOrder.Status.ACQUIRED or _already_billed(
        imaging_order=order, is_current_imaging_charge=True,
    ):
        return None
    service = order.billing_service
    if service is None or service.category != Service.Category.IMAGING or not service.is_active:
        logger.warning('Imaging order #%s has no active imaging service; it was not billed.', order.pk)
        return None
    source = {'imaging_order': order}
    if appointment is not None:
        source['appointment'] = appointment
    return _safely(f'imaging order #{order.pk}', lambda: _create_invoice(
        order.patient, [(service, 1, source)]))
