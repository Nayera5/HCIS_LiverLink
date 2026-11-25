"""
Lab business rules.

    handle_inbound()   an ORM^O01 arrived: create (or cancel) the order and return the ACK
    set_status()       move the sample: Received -> Processing -> Completed
    save_results()     lab staff entered values (only while Processing)
    send_results()     build the ORU^R01, send it to LiverLink and check its ACK
"""
import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from . import hl7, mllp
from .catalog import defaults_for
from .models import Message, Order, OrderTest

logger = logging.getLogger(__name__)
S = Order.Status

# Completed can go back to Processing, to correct a value before (or after a refused) sending.
ALLOWED_MOVES = {
    S.RECEIVED: {S.PROCESSING},
    S.PROCESSING: {S.RECEIVED, S.COMPLETED},
    S.COMPLETED: {S.PROCESSING},
    S.CANCELLED: set(),
}


class LabError(Exception):
    """A rule was broken: shown to lab staff, or answered with AE when it came in an HL7 message."""


# ================================================================ inbound: orders

def handle_inbound(raw):
    """Log, process and acknowledge one received message. Always returns an ACK."""
    log = Message(direction='inbound', raw_message=raw.replace('\x00', ''))
    header = {}
    try:
        message = hl7.parse(raw)
        header = hl7.read_header(message)
    except hl7.HL7FormatError as e:
        return _finish(log, header, 'AR', str(e))

    log.message_type, log.control_id = header['type'][:20], header['control_id'][:50]
    if not log.control_id:
        return _finish(log, header, 'AR', 'Message control ID (MSH-10) is missing.')
    if header['type'] != 'ORM^O01':
        return _finish(log, header, 'AR', f'Message type {header["type"]} is not supported.')
    if Message.objects.filter(direction='inbound', control_id=log.control_id, status='processed').exists():
        return hl7.build_ack(header, 'AA', 'Duplicate: already processed.')  # e.g. our first ACK was lost

    try:
        with transaction.atomic():
            _apply_order(header['sender'], hl7.parse_orm(message))
    except (hl7.HL7FormatError, LabError) as e:
        return _finish(log, header, 'AE', str(e))
    except Exception:
        logger.exception('HL7 message %s could not be processed', log.control_id)
        return _finish(log, header, 'AE', 'Internal error in the lab system.')
    return _finish(log, header, 'AA')


def _finish(log, header, code, error=''):
    log.ack_code, log.error_text = code, error
    log.status = 'processed' if code == 'AA' else 'error'
    log.ack_message = hl7.build_ack(header, code, error)
    log.save()
    return log.ack_message


def _apply_order(sender, data):
    order = Order.objects.filter(sender=sender, placer_order_id=data['order_id']).first()

    if data['control'] == 'CA':
        if order is None:
            raise LabError(f'Order {data["order_id"]} is not known here.')
        if order.mrn != data['mrn']:
            raise LabError('The patient MRN does not match the order.')
        if order.results_sent_at:
            raise LabError('Results were already reported.')
        order.status = S.CANCELLED
        order.save(update_fields=['status'])
        return

    if data['control'] != 'NW':
        raise LabError(f'Order control "{data["control"]}" is not supported.')
    if order is not None:
        raise LabError(f'Order {data["order_id"]} already exists.')
    if not data['tests']:
        raise LabError('The order has no tests (OBR).')

    order = Order.objects.create(
        sender=sender, placer_order_id=data['order_id'], mrn=data['mrn'], last_name=data['last_name'],
        first_name=data['first_name'], birth_date=data['birth_date'], sex=data['sex'],
        priority=data['priority'], ordered_by=data['ordered_by'])
    order.accession_number = f'ACC-{timezone.localdate():%Y%m%d}-{order.pk:04d}'
    order.save(update_fields=['accession_number'])
    for code, name in data['tests']:
        unit, reference_range = defaults_for(code)
        OrderTest.objects.create(order=order, code=code, name=name, unit=unit, reference_range=reference_range)


# ================================================================ lab staff actions

def set_status(order, new_status):
    if order.results_sent_at:
        raise LabError('Results were already sent.')
    if new_status not in ALLOWED_MOVES[order.status]:
        raise LabError(f'A {order.get_status_display().lower()} sample cannot be changed to "{new_status}".')
    if new_status == S.COMPLETED and order.tests.filter(value='').exists():
        raise LabError('Enter and save all results before completing the sample.')
    order.status = new_status
    order.save(update_fields=['status'])


@transaction.atomic
def save_results(order, rows):
    """rows: [{id, value, unit, reference_range, flag}]. An empty value clears the result."""
    if order.status != S.PROCESSING:
        raise LabError('Results can only be entered while the sample is processing.')
    tests = {t.pk: t for t in order.tests.all()}
    for row in rows:
        test = tests.get(row['id']) if isinstance(row, dict) and isinstance(row.get('id'), int) else None
        if test is None:
            raise LabError('Unknown test.')
        value, unit, reference_range, flag = (
            str(row.get(key) or '').strip() for key in ('value', 'unit', 'reference_range', 'flag'))
        if value:
            _check_number(test, value)
            if flag not in OrderTest.FLAGS:
                raise LabError(f'{test.name}: choose a flag.')
        if len(unit) > 30 or len(reference_range) > 50:
            raise LabError(f'{test.name}: unit or reference range is too long.')
        if value != test.value:
            test.result_time = timezone.now() if value else None
        test.value, test.unit, test.reference_range = value, unit, reference_range
        test.flag = flag if value else ''
        test.save()


def _check_number(test, value):
    try:
        number = Decimal(value)
    except InvalidOperation:
        number = None
    # Plain digits only: HL7 type NM does not allow forms such as 1e5.
    if number is None or not value.isascii() or not value.replace('.', '', 1).isdigit() or len(value) > 12:
        raise LabError(f'{test.name}: "{value}" is not a valid positive number.')


def send_results(order):
    """Returns the Message that was sent (status 'sent' or 'error')."""
    if order.results_sent_at:
        raise LabError('Results were already sent.')
    if order.status != S.COMPLETED:
        raise LabError('Complete the sample before sending its results.')
    control_id = hl7.new_control_id()
    log = Message(direction='outbound', message_type='ORU^R01', control_id=control_id,
                  raw_message=hl7.build_oru(order, control_id))
    try:
        log.ack_message = mllp.send(settings.LIVERLINK_HOST, settings.LIVERLINK_PORT, log.raw_message)
        code, text, answered_id = hl7.parse_ack(log.ack_message)
        if answered_id != control_id:
            raise hl7.HL7FormatError('The ACK answers a different message.')
        log.ack_code = code
        log.status = 'sent' if code == 'AA' else 'error'
        log.error_text = '' if code == 'AA' else text
    except (mllp.MLLPError, hl7.HL7FormatError) as e:
        log.status, log.error_text = 'error', str(e)
    log.save()
    if log.status == 'sent':
        order.results_sent_at = timezone.now()
        order.save(update_fields=['results_sent_at'])
    return log
