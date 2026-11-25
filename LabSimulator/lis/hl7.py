"""
HL7 v2.5 messages (built and parsed with HL7apy). This file knows HL7 syntax only: no database.

    parse_orm()    ORM^O01  message -> plain dict
    build_oru()    ORU^R01  Order   -> message text
    build_ack()    ACK      answer to a received message
    parse_ack()    ACK      -> (code, text, control id it answers)

The helpers look like those in Backend/apps/hl7/message.py on purpose: each system keeps its own
copy, as two real systems from different vendors would.
"""
import uuid
from datetime import datetime, timezone

from django.conf import settings
from hl7apy.core import Message
from hl7apy.exceptions import HL7apyException
from hl7apy.parser import parse_message

VERSION = '2.5'


class HL7FormatError(Exception):
    """The message is not valid HL7, or a required field is missing or wrong."""


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


def new_control_id():
    return f'LAB{uuid.uuid4().hex[:17].upper()}'  # MSH-10 is at most 20 characters


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
    msh.msh_3 = settings.APP_NAME
    msh.msh_4 = 'LAB'
    msh.msh_5 = escape(receiver)
    msh.msh_7 = hl7_time()
    msh.msh_9 = message_type
    msh.msh_10 = control_id
    msh.msh_11 = 'P'
    msh.msh_12 = VERSION
    msh.msh_18 = 'UNICODE UTF-8'
    return message


# ---------------------------------------------------------------- ORM^O01 (order in)

def parse_orm(message):
    """-> {control, order_id, mrn, last_name, …, tests: [(code, name)]}"""
    data = {'control': '', 'order_id': '', 'mrn': '', 'tests': []}
    for segment in message.children:
        if segment.name == 'PID':
            data['mrn'] = field(segment, 'pid_3')
            data['last_name'] = field(segment, 'pid_5', 1)
            data['first_name'] = field(segment, 'pid_5', 2)
            data['birth_date'] = field(segment, 'pid_7')
            data['sex'] = field(segment, 'pid_8')
        elif segment.name == 'ORC':
            order_id = field(segment, 'orc_2')
            if data['order_id'] and order_id != data['order_id']:
                raise HL7FormatError('One ORM message may carry only one order (ORC-2).')
            data['control'], data['order_id'] = field(segment, 'orc_1'), order_id
            data['ordered_by'] = f"{field(segment, 'orc_12', 3)} {field(segment, 'orc_12', 2)}".strip()
        elif segment.name == 'OBR':
            data['priority'] = 'routine' if field(segment, 'obr_5') in ('', 'R') else 'urgent'
            code = field(segment, 'obr_4', 1)
            if not code:
                raise HL7FormatError('Test code (OBR-4) is missing.')
            data['tests'].append((code, field(segment, 'obr_4', 2) or code))
    if not data['order_id']:
        raise HL7FormatError('Order ID (ORC-2) is missing.')
    if not data['mrn']:
        raise HL7FormatError('Patient MRN (PID-3) is missing.')
    return data


# ---------------------------------------------------------------- ORU^R01 (results out)

def build_oru(order, control_id):
    """One OBR + OBX pair per test. All values must be entered already."""
    message = _new_message('ORU_R01', 'ORU^R01^ORU_R01', order.sender, control_id)
    result_group = message.add_group('ORU_R01_PATIENT_RESULT')
    pid = result_group.add_group('ORU_R01_PATIENT').pid
    pid.pid_1 = '1'
    pid.pid_3 = f'{escape(order.mrn)}^^^{escape(order.sender)}^MR'
    pid.pid_5 = f'{escape(order.last_name)}^{escape(order.first_name)}'
    pid.pid_7 = escape(order.birth_date)
    pid.pid_8 = escape(order.sex)

    for number, test in enumerate(order.tests.all(), start=1):
        test_id = f'{escape(test.code)}^{escape(test.name)}^LN'
        group = result_group.add_group('ORU_R01_ORDER_OBSERVATION')
        orc = group.orc
        orc.orc_1 = 'RE'
        orc.orc_2 = f'{escape(order.placer_order_id)}^{escape(order.sender)}'
        orc.orc_3 = f'{order.accession_number}^{settings.APP_NAME}'  # filler order number = accession number
        obr = group.obr
        obr.obr_1 = str(number)
        obr.obr_2 = f'{escape(order.placer_order_id)}^{escape(order.sender)}'
        obr.obr_3 = f'{order.accession_number}^{settings.APP_NAME}'
        obr.obr_4 = test_id
        obr.obr_22 = hl7_time()
        obr.obr_25 = 'F'
        obx = group.add_group('ORU_R01_OBSERVATION').obx
        obx.obx_1 = '1'
        obx.obx_2 = 'NM'
        obx.obx_3 = test_id
        obx.obx_5 = test.value
        obx.obx_6 = escape(test.unit)
        obx.obx_7 = escape(test.reference_range)
        obx.obx_8 = test.flag
        obx.obx_11 = 'F'
        obx.obx_14 = hl7_time(test.result_time)
    return message.to_er7()


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
