"""The single page and the small JSON API behind it."""
import json

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from . import services
from .models import Message, Order

MAX_ROWS = 200  # newest orders / messages shown


@ensure_csrf_cookie
@require_GET
def index(request):
    return render(request, 'lis/index.html', {
        'hl7_in': f'{settings.HL7_HOST}:{settings.HL7_PORT}',
        'hl7_out': f'{settings.LIVERLINK_HOST}:{settings.LIVERLINK_PORT}',
    })


# ---------------------------------------------------------------- orders

def _order_row(order):
    return {
        'id': order.pk,
        'accession_number': order.accession_number,
        'placer_order_id': order.placer_order_id,
        'mrn': order.mrn,
        'patient_name': f'{order.first_name} {order.last_name}'.strip(),
        'priority': order.priority,
        'status': order.status,
        'received_at': order.received_at,
        'results_sent_at': order.results_sent_at,
    }


def _order_full(order):
    return _order_row(order) | {
        'sender': order.sender,
        'birth_date': order.birth_date,
        'sex': order.sex,
        'ordered_by': order.ordered_by,
        'allowed_moves': [] if order.results_sent_at else sorted(services.ALLOWED_MOVES[order.status]),
        'tests': list(order.tests.values('id', 'code', 'name', 'value', 'unit', 'reference_range', 'flag')),
    }


def _bad(error):
    return JsonResponse({'detail': str(error)}, status=400)


def _body(request):
    try:
        data = json.loads(request.body or '{}')
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


@require_GET
def order_list(request):
    return JsonResponse({'orders': [_order_row(o) for o in Order.objects.all()[:MAX_ROWS]]})


@require_GET
def order_detail(request, pk):
    return JsonResponse(_order_full(get_object_or_404(Order, pk=pk)))


@require_POST
def change_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    try:
        services.set_status(order, str(_body(request).get('status')))
    except services.LabError as e:
        return _bad(e)
    return JsonResponse(_order_full(order))


@require_POST
def save_results(request, pk):
    order = get_object_or_404(Order, pk=pk)
    rows = _body(request).get('results')
    if not isinstance(rows, list):
        return _bad('No results were sent.')
    try:
        services.save_results(order, rows)
    except services.LabError as e:
        return _bad(e)
    return JsonResponse(_order_full(order))


@require_POST
def send_results(request, pk):
    order = get_object_or_404(Order, pk=pk)
    try:
        log = services.send_results(order)
    except services.LabError as e:
        return _bad(e)
    if log.status != 'sent':
        return _bad(f'LiverLink did not accept the results: {log.error_text}')
    return JsonResponse(_order_full(order))


# ---------------------------------------------------------------- HL7 Message Monitor

MESSAGE_FIELDS = ['id', 'created_at', 'direction', 'message_type', 'control_id', 'ack_code', 'status', 'error_text']


@require_GET
def message_list(request):
    return JsonResponse({'messages': list(Message.objects.values(*MESSAGE_FIELDS)[:MAX_ROWS])})


@require_GET
def message_detail(request, pk):
    log = get_object_or_404(Message.objects.values(*MESSAGE_FIELDS, 'raw_message', 'ack_message'), pk=pk)
    return JsonResponse(log)
