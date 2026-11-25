"""
HL7 business logic.

Outbound: labs.services calls queue_order() when an order is placed or cancelled. The message is
saved in the same transaction and sent after it commits, on a background thread, so a lab that is
down never blocks the doctor. A failed message stays in the log and can be resent.

Inbound: the listener (manage.py hl7_listener) passes every message to handle_inbound(), which logs
it, saves the results through labs.services.record_result() and returns the ACK.
"""
import logging
import threading
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import close_old_connections, transaction

from apps.accounts.models import AuditLog
from apps.labs.models import LabOrder

from . import message as hl7
from . import mllp
from .models import ExternalSystem, HL7Message

logger = logging.getLogger(__name__)

D, S = HL7Message.Direction, HL7Message.Status
MAX_VALUE = Decimal('100000000')  # LabResult.value holds 8 digits before the point


class HL7ProcessingError(Exception):
    """The message was understood but breaks a rule: answered with AE, nothing is saved."""


class ResendError(Exception):
    """This message cannot be resent (reported to the caller as a 400)."""


# ================================================================ outbound: orders

def queue_order(order, control):
    """Queue an ORM^O01 for the external lab. control: 'NW' (new) or 'CA' (cancel)."""
    lab = ExternalSystem.objects.filter(system_type=ExternalSystem.SystemType.EXTERNAL_LAB,
                                        is_active=True).first()
    if lab is None:
        return None  # no lab connected: results are entered by hand
    control_id = hl7.new_control_id()
    msg = HL7Message.objects.create(
        system=lab, patient=order.patient, direction=D.OUTBOUND, message_type='ORM^O01', control_id=control_id,
        raw_message=hl7.build_orm(order, lab.name, control, control_id), status=S.QUEUED)
    if settings.HL7_SEND_ASYNC:
        transaction.on_commit(lambda: threading.Thread(
            target=_send_in_background, args=(msg.pk,), daemon=True, name=f'hl7-send-{msg.pk}').start())
    else:
        transaction.on_commit(lambda: send_now(msg))
    return msg


def _send_in_background(message_id):
    try:
        send_now(HL7Message.objects.get(pk=message_id))
    except Exception:
        logger.exception('Sending HL7 message %s failed', message_id)
    finally:
        close_old_connections()  # this thread opened its own database connection


def send_now(msg):
    """Send a logged outbound message, check the ACK and record the outcome."""
    msg.ack_code, msg.ack_message, msg.error_text = '', '', ''
    try:
        _check_still_wanted(msg)
        msg.ack_message = mllp.send(msg.system.host, msg.system.port, msg.raw_message)
        code, text, answered_id = hl7.parse_ack(msg.ack_message)
        if answered_id != msg.control_id:
            raise hl7.HL7FormatError('The ACK answers a different message.')
        msg.ack_code = code
        msg.status = S.SENT if code == 'AA' else S.ERROR
        msg.error_text = '' if code == 'AA' else text
    except (mllp.MLLPError, hl7.HL7FormatError, HL7ProcessingError) as e:
        msg.status, msg.error_text = S.ERROR, str(e)
    msg.save(update_fields=['ack_code', 'ack_message', 'status', 'error_text'])
    return msg


def _check_still_wanted(msg):
    """Never send a *new order* message for an order that was cancelled in the meantime."""
    orc = next((s for s in hl7.parse(msg.raw_message).children if s.name == 'ORC'), None)
    if hl7.field(orc, 'orc_1') != 'NW':
        return
    order = LabOrder.objects.filter(pk=hl7.field(orc, 'orc_2')).first()
    if order is None or order.status == LabOrder.Status.CANCELLED:
        raise HL7ProcessingError('The order was cancelled, so it was not sent.')


def resend(msg):
    """Same message, same control ID: the receiver recognises it if it did arrive the first time."""
    if msg.direction != D.OUTBOUND or msg.status not in (S.ERROR, S.QUEUED):
        raise ResendError('Only outbound messages that failed can be resent.')
    if not msg.system.is_active:
        raise ResendError(f'{msg.system.name} is inactive.')
    return send_now(msg)


# ================================================================ inbound: results

def handle_inbound(raw):
    """Log, process and acknowledge one received message. Always returns an ACK."""
    log = HL7Message(direction=D.INBOUND, message_type='unknown', raw_message=raw.replace('\x00', ''),
                     status=S.RECEIVED)
    header = {}
    try:
        message = hl7.parse(raw)
        header = hl7.read_header(message)
        log.message_type = header['type'][:20]
        log.control_id = header['control_id'][:50]
        log.system = ExternalSystem.objects.filter(name=header['sender']).first()
    except hl7.HL7FormatError as e:
        return _finish(log, header, 'AR', str(e))

    if log.system is None:
        return _finish(log, header, 'AR', f'Unknown sender "{header["sender"]}".')
    if not log.system.is_active:
        return _finish(log, header, 'AR', 'This system is inactive in LiverLink.')
    if not log.control_id:
        return _finish(log, header, 'AR', 'Message control ID (MSH-10) is missing.')
    if header['type'] != 'ORU^R01':
        return _finish(log, header, 'AR', f'Message type {header["type"]} is not supported.')
    if HL7Message.objects.filter(system=log.system, direction=D.INBOUND, control_id=log.control_id,
                                 status=S.PROCESSED).exists():
        return hl7.build_ack(header, 'AA', 'Duplicate: already processed.')  # e.g. our first ACK was lost

    log.save()
    try:
        with transaction.atomic():
            _save_results(hl7.parse_oru(message), log)
    except (hl7.HL7FormatError, HL7ProcessingError) as e:
        return _finish(log, header, 'AE', str(e))
    except Exception:
        logger.exception('HL7 message %s could not be processed', log.pk)
        return _finish(log, header, 'AE', 'Internal error while saving the results.')
    return _finish(log, header, 'AA')


def _finish(log, header, code, error=''):
    log.ack_code, log.error_text = code, error
    log.status = S.PROCESSED if code == 'AA' else S.ERROR
    log.ack_message = hl7.build_ack(header, code, error)
    log.save()
    return log.ack_message


def _save_results(data, log):
    """Check the whole message first, then save: either every result is saved or none."""
    from apps.labs import services as lab_services  # imported here: labs.services imports this module

    order = None
    if data['order_id'].isascii() and data['order_id'].isdigit() and len(data['order_id']) <= 18:
        order = LabOrder.objects.select_for_update().filter(pk=int(data['order_id'])).first()
    if order is None:
        raise HL7ProcessingError(f'Unknown order "{data["order_id"]}".')
    if order.patient.mrn != data['mrn']:
        raise HL7ProcessingError('The patient MRN does not match the order.')
    log.patient = order.patient  # also shown in the monitor when the message is refused below
    if order.status == LabOrder.Status.CANCELLED:
        raise HL7ProcessingError('This order was cancelled.')

    ordered = {r.lab_test.code: r for r in order.results.select_related('lab_test')}
    to_save = []
    for item in data['results']:
        result = ordered.pop(item['code'], None)  # popped, so a repeated code is refused as well
        if result is None:
            raise HL7ProcessingError(f'Test "{item["code"]}" is not in this order, or is repeated.')
        value = _numeric(item)
        unit = result.lab_test.unit
        if item['unit'].lower() != unit.lower():
            raise HL7ProcessingError(f'{item["code"]}: unit is "{item["unit"]}", expected "{unit}".')
        if item['status'] not in ('F', 'C'):
            raise HL7ProcessingError(f'{item["code"]}: only final or corrected results are accepted.')
        if result.value is not None and item['status'] != 'C':
            if result.value != value:
                raise HL7ProcessingError(f'{item["code"]} already has a different result.')
            continue  # the same value again: nothing to do
        to_save.append((result, value, item['time']))

    for result, value, time in to_save:
        # The flag is set by LiverLink from its own ranges (spec 4.17); the lab's flag stays in the log.
        result.lab_order = order  # share one instance, so the order status is refreshed only once
        lab_services.record_result(result, value, time, hl7_message=log)
        AuditLog.record(AuditLog.Action.UPDATE, 'labs.labresult', actor=f'HL7: {log.system.name}',
                        entity_id=result.pk, patient=order.patient)


def _numeric(item):
    try:
        value = Decimal(item['value']) if item['value_type'] == 'NM' else None
    except InvalidOperation:
        value = None
    if value is None or not value.is_finite() or not 0 <= value < MAX_VALUE:
        raise HL7ProcessingError(f'{item["code"]}: "{item["value"]}" is not a valid number.')
    return value.quantize(Decimal('0.0001'))  # as stored
