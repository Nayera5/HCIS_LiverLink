"""
HL7 v2.5 messages (built and parsed with HL7apy). This file knows HL7 syntax only: no database.

    build_orm()    ORM^O01  LabOrder -> message text
    parse_oru()    ORU^R01  message  -> plain dict
    build_ack()    ACK      answer to a received message
    parse_ack()    ACK      -> (code, text, control id it answers)
"""
import uuid
from datetime import datetime, timezone

from hl7apy.core import Message
from hl7apy.exceptions import HL7apyException
from hl7apy.parser import parse_message

APP_NAME = 'LIVERLINK'
VERSION = '2.5'
PRIORITY_CODES = {'routine': 'R', 'urgent': 'A'}  # HL7: A = as soon as possible
SEX_CODES = {'male': 'M', 'female': 'F'}


class HL7FormatError(Exception):
    """The message is not valid HL7, or a required field is missing or wrong."""


# ---------------------------------------------------------------- small helpers

# HL7 uses these characters as separators, so they are escaped inside free text (e.g. names).
_ESCAPES = [('\\', '\\E\\'), ('|', '\\F\\'), ('^', '\\S\\'), ('&', '\\T\\'), ('~', '\\R\\')]


def escape(value):
    text = str(value if value is not None else '').replace('\r', ' ').replace('\n', ' ')
    for char, code in _ESCAPES:
        text = text.replace(char, code)
    return text


def unescape(text):
    for char, code in reversed(_ESCAPES):
        text = text.replace(code, char)
    return text


def field(segment, name, component=1):
    """One component of a field, e.g. field(pid, 'pid_3') -> 'LL-000001'. '' when empty."""
    if segment is None:
        return ''
    parts = (getattr(segment, name).value or '').split('^')
    return unescape(parts[component - 1]).strip() if len(parts) >= component else ''


def hl7_time(moment=None):
    return (moment or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime('%Y%m%d%H%M%S+0000')


def parse_time(text):
    """HL7 timestamp -> aware datetime (UTC when no offset is given), or None when empty."""
    if not text:
        return None
    for fmt in ('%Y%m%d%H%M%S%z', '%Y%m%d%H%M%S', '%Y%m%d%H%M', '%Y%m%d'):
        try:
            moment = datetime.strptime(text, fmt)
        except ValueError:
            continue
        return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
    raise HL7FormatError(f'Invalid date/time "{text}".')


def new_control_id():
    return f'LL{uuid.uuid4().hex[:18].upper()}'  # MSH-10 is at most 20 characters


def parse(raw):
    try:
        return parse_message(raw.replace('\r\n', '\r').replace('\n', '\r').strip(), find_groups=False)
    except HL7apyException as e:
        raise HL7FormatError(f'Not a valid HL7 message: {e}') from e
    except Exception as e:  # HL7apy raises plain Python errors on some broken input
        raise HL7FormatError('Not a valid HL7 message.') from e


def read_header(message):
    msh = message.msh
    return {
        'sender': field(msh, 'msh_3'),
        'type': f"{field(msh, 'msh_9', 1)}^{field(msh, 'msh_9', 2)}",
        'trigger': field(msh, 'msh_9', 2),
        'control_id': field(msh, 'msh_10'),
    }


def _new_message(structure, message_type, receiver, control_id):
    message = Message(structure, version=VERSION)
    msh = message.msh
    msh.msh_3 = APP_NAME
    msh.msh_4 = 'LIVER_CENTER'
    msh.msh_5 = escape(receiver)
    msh.msh_7 = hl7_time()
    msh.msh_9 = message_type
    msh.msh_10 = control_id
    msh.msh_11 = 'P'
    msh.msh_12 = VERSION
    msh.msh_18 = 'UNICODE UTF-8'
    return message


# ---------------------------------------------------------------- ORM^O01 (order out)

def build_orm(order, receiver, control, control_id):
    """control: 'NW' (new order) or 'CA' (cancel). One ORC + OBR pair per requested test."""
    patient = order.patient
    doctor = order.ordered_by.user
    provider = f'{order.ordered_by_id}^{escape(doctor.last_name or doctor.username)}^{escape(doctor.first_name)}'

    message = _new_message('ORM_O01', 'ORM^O01^ORM_O01', receiver, control_id)
    pid = message.add_group('ORM_O01_PATIENT').pid
    pid.pid_1 = '1'
    pid.pid_3 = f'{escape(patient.mrn)}^^^{APP_NAME}^MR'
    pid.pid_5 = f'{escape(patient.last_name)}^{escape(patient.first_name)}'
    pid.pid_7 = patient.date_of_birth.strftime('%Y%m%d')
    pid.pid_8 = SEX_CODES.get(patient.sex, 'U')

    for number, result in enumerate(order.results.select_related('lab_test'), start=1):
        test = result.lab_test
        group = message.add_group('ORM_O01_ORDER')
        orc = group.orc
        orc.orc_1 = control
        orc.orc_2 = f'{order.pk}^{APP_NAME}'       # placer order number = LiverLink's internal order ID
        orc.orc_9 = hl7_time(order.order_date)
        orc.orc_12 = provider
        obr = group.add_group('ORM_O01_ORDER_DETAIL').obr
        obr.obr_1 = str(number)
        obr.obr_2 = f'{order.pk}^{APP_NAME}'
        obr.obr_4 = f'{escape(test.code)}^{escape(test.name)}^LN'
        obr.obr_5 = PRIORITY_CODES[order.priority]
        obr.obr_16 = provider
    return message.to_er7()


# ---------------------------------------------------------------- ORU^R01 (results in)

def parse_oru(message):
    """-> {mrn, order_id, accession, results: [{code, value_type, value, unit, flag, status, time}]}"""
    data = {'mrn': '', 'order_id': '', 'accession': '', 'results': []}
    for segment in message.children:
        if segment.name == 'PID':
            data['mrn'] = field(segment, 'pid_3')
        elif segment.name == 'OBR':
            order_id = field(segment, 'obr_2')
            if data['order_id'] and order_id != data['order_id']:
                raise HL7FormatError('One ORU message may report only one order (OBR-2).')
            data['order_id'] = order_id
            data['accession'] = field(segment, 'obr_3')
        elif segment.name == 'OBX':
            data['results'].append({
                'code': field(segment, 'obx_3'),
                'value_type': field(segment, 'obx_2'),
                'value': field(segment, 'obx_5'),
                'unit': field(segment, 'obx_6'),
                'flag': field(segment, 'obx_8'),
                'status': field(segment, 'obx_11'),
                'time': parse_time(field(segment, 'obx_14')),
            })
    if not data['mrn']:
        raise HL7FormatError('Patient MRN (PID-3) is missing.')
    if not data['order_id']:
        raise HL7FormatError('Order ID (OBR-2) is missing.')
    if not data['results']:
        raise HL7FormatError('The message has no results (OBX).')
    return data


# ---------------------------------------------------------------- ACK

def build_ack(header, code, text=''):
    """Answer `header` (from read_header) with AA (accepted), AE (error) or AR (rejected)."""
    trigger = header.get('trigger') or ''
    message_type = f'ACK^{trigger}^ACK' if trigger.isalnum() else 'ACK'
    message = _new_message('ACK', message_type, header.get('sender', ''), new_control_id())
    message.msa.msa_1 = code
    message.msa.msa_2 = escape(header.get('control_id', ''))
    if text:
        message.msa.msa_3 = escape(text[:80])  # MSA-3 is at most 80 characters
    return message.to_er7()


def parse_ack(raw):
    """-> (code, text, control id being acknowledged)"""
    message = parse(raw)
    msa = next((s for s in message.children if s.name == 'MSA'), None)
    code = field(msa, 'msa_1')
    if code not in ('AA', 'AE', 'AR'):
        raise HL7FormatError('The answer is not a valid ACK.')
    return code, field(msa, 'msa_3'), field(msa, 'msa_2')
