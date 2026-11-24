"""
Online payment through Paymob (Egypt), test (sandbox) mode (spec §13 "Online Payment").

Flow:
1. start_online_payment(): the patient clicks "Pay online". We create a *pending* Payment for the
   invoice balance, then ask Paymob for a payment intention and send the browser to Unified
   Checkout.
2. The patient pays on Paymob's page.
3. Paymob reports the transaction twice. Both are signed with HMAC and both go through
   apply_result(), which is idempotent:
   - Transaction processed callback: Paymob's server POSTs to /api/payments/paymob/callback/.
     It only arrives if Paymob can reach this server (deployed, or a tunnel such as ngrok:
     see PAYMOB_CALLBACK_BASE_URL).
   - Transaction response callback: the browser is redirected (GET) to
     /api/payments/paymob/return/. It works on localhost too, and then redirects to the invoice page.

Payments are matched by Paymob's order id (saved from the intention response). Our receipt number
is also sent as `special_reference`, and is used as a fallback when the order id is unknown.

Confirmed on Paymob's docs (Transaction callback HMAC page): the 20 HMAC fields and their order,
HMAC-SHA512 hex digest, `hmac` query parameter, lowercase booleans, `id` / `order_id` names on
the GET callback, and the Egypt checkout URL.
Not confirmed on an official page, so check these against a real sandbox payment:
- the create-intention body (taken from Paymob's published example);
- the GET names of the source_data fields ('source_data.pan' or 'source_data_pan'; both are accepted);
- how null values are written in the HMAC string (an empty string is used here).
"""
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.request
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Invoice, Payment

logger = logging.getLogger(__name__)

CURRENCY = 'EGP'


class PaymobError(Exception):
    """Paymob is not configured, refused the request, or could not be reached."""


class NotPayable(PaymobError):
    """The invoice cannot be paid online (closed, or nothing left to pay)."""


# --------------------------------------------------------------------------- configuration

def config():
    return settings.PAYMOB


def is_configured():
    c = config()
    return bool(c['SECRET_KEY'] and c['PUBLIC_KEY'] and c['HMAC_SECRET'] and c['INTEGRATION_IDS'])


def checkout_url(client_secret):
    base = config()['CHECKOUT_URL'].rstrip('/')
    return f"{base}/?publicKey={config()['PUBLIC_KEY']}&clientSecret={client_secret}"


# --------------------------------------------------------------------------- HMAC

# (key path in the POST callback's `obj`, accepted key names in the GET redirect's query string)
HMAC_FIELDS = [
    ('amount_cents', ('amount_cents',)),
    ('created_at', ('created_at',)),
    ('currency', ('currency',)),
    ('error_occured', ('error_occured',)),
    ('has_parent_transaction', ('has_parent_transaction',)),
    ('id', ('id',)),
    ('integration_id', ('integration_id',)),
    ('is_3d_secure', ('is_3d_secure',)),
    ('is_auth', ('is_auth',)),
    ('is_capture', ('is_capture',)),
    ('is_refunded', ('is_refunded',)),
    ('is_standalone_payment', ('is_standalone_payment',)),
    ('is_voided', ('is_voided',)),
    ('order.id', ('order_id', 'order')),
    ('owner', ('owner',)),
    ('pending', ('pending',)),
    ('source_data.pan', ('source_data.pan', 'source_data_pan')),
    ('source_data.sub_type', ('source_data.sub_type', 'source_data_sub_type')),
    ('source_data.type', ('source_data.type', 'source_data_type')),
    ('success', ('success',)),
]


def _text(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return '' if value is None else str(value)


def _dig(obj, path):
    for part in path.split('.'):
        if not isinstance(obj, dict):
            return None
        obj = obj.get(part)
    return obj


def _sign(message):
    return hmac.new(config()['HMAC_SECRET'].encode(), message.encode(), hashlib.sha512).hexdigest()


def hmac_for_processed(obj):
    """HMAC of a transaction processed (POST) callback's `obj`."""
    return _sign(''.join(_text(_dig(obj, path)) for path, _ in HMAC_FIELDS))


def hmac_for_response(params):
    """HMAC of a transaction response (GET redirect) callback's query parameters."""
    def value(names):
        for name in names:
            if name in params:
                return params[name]
        return ''
    return _sign(''.join(_text(value(names)) for _, names in HMAC_FIELDS))


def signature_ok(expected, received):
    return bool(received) and hmac.compare_digest(expected, str(received).lower())


# --------------------------------------------------------------------------- Paymob API

def _post(path, body):
    url = f"{config()['API_URL'].rstrip('/')}{path}"
    request = urllib.request.Request(
        url, data=json.dumps(body).encode(), method='POST',
        headers={'Authorization': f"Token {config()['SECRET_KEY']}", 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode() or '{}')
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors='replace')[:500]
        logger.error('Paymob %s returned %s: %s', path, exc.code, detail)
        raise PaymobError(f'Paymob refused the request ({exc.code}).') from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        logger.error('Paymob %s failed: %s', path, exc)
        raise PaymobError('Could not reach Paymob. Please try again.') from exc


def _billing_data(patient):
    user = patient.user
    na = 'NA'  # Paymob requires every billing field; we only collect some of them.
    return {
        'first_name': patient.first_name or na,
        'last_name': patient.last_name or na,
        'email': (user.email if user and user.email else 'no-email@liverlink.local'),
        'phone_number': patient.phone or na,
        'country': 'EG', 'city': na, 'street': na, 'building': na, 'floor': na, 'apartment': na,
    }


def create_intention(payment, *, redirection_url, notification_url=''):
    invoice = payment.invoice
    cents = int((payment.amount * 100).to_integral_value())
    body = {
        'amount': cents,
        'currency': CURRENCY,
        'payment_methods': config()['INTEGRATION_IDS'],
        'items': [{'name': f'Invoice {invoice.invoice_no}', 'amount': cents, 'quantity': 1,
                   'description': f'LiverLink invoice {invoice.invoice_no}'}],
        'billing_data': _billing_data(invoice.patient),
        'special_reference': payment.receipt_no,
        'redirection_url': redirection_url,
    }
    if notification_url:
        body['notification_url'] = notification_url
    data = _post('/v1/intention/', body)
    if not data.get('client_secret'):
        logger.error('Paymob intention response has no client_secret: %s', str(data)[:500])
        raise PaymobError('Paymob did not return a checkout session.')
    return data


# --------------------------------------------------------------------------- our side

def outstanding(invoice):
    return invoice.total_amount - invoice.paid_amount()


def start_online_payment(invoice, *, redirection_url, notification_url=''):
    """Create a pending online payment for the invoice balance. Returns (payment, checkout URL)."""
    if not is_configured():
        raise PaymobError('Online payment is not available right now.')
    with transaction.atomic():
        invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
        if invoice.status not in Invoice.OPEN_STATUSES:
            raise NotPayable(f'An invoice that is {invoice.get_status_display().lower()} cannot be paid.')
        balance = outstanding(invoice)
        if balance <= 0:
            raise NotPayable('This invoice has nothing left to pay.')
        payment = Payment.objects.create(invoice=invoice, method=Payment.Method.ONLINE,
                                         status=Payment.Status.PENDING, amount=balance)
    try:
        intention = create_intention(payment, redirection_url=redirection_url, notification_url=notification_url)
    except PaymobError:
        Payment.objects.filter(pk=payment.pk).update(status=Payment.Status.FAILED)
        raise
    payment.gateway_order_id = str(intention.get('intention_order_id') or '')
    payment.save(update_fields=['gateway_order_id'])
    return payment, checkout_url(intention['client_secret'])


def _find_payment(order_id, reference):
    qs = Payment.objects.select_for_update().filter(method=Payment.Method.ONLINE)
    payment = qs.filter(gateway_order_id=str(order_id)).first() if order_id not in (None, '') else None
    if payment is None and reference:
        payment = qs.filter(receipt_no=str(reference)).first()
    return payment


def apply_result(*, order_id, txn_id, success, pending, amount_cents, reference=None):
    """
    Record a Paymob transaction result on our pending payment. Safe to call more than once for
    the same transaction (the callback and the redirect both call it). Returns the payment, or
    None when no payment matches.
    """
    with transaction.atomic():
        payment = _find_payment(order_id, reference)
        if payment is None:
            logger.warning('Paymob result for unknown order %s (reference %s)', order_id, reference)
            return None
        invoice = Invoice.objects.select_for_update().get(pk=payment.invoice_id)
        payment.invoice = invoice
        if payment.status == Payment.Status.SUCCEEDED or pending:
            return payment  # already recorded, or Paymob has no final answer yet
        if order_id and not payment.gateway_order_id:
            payment.gateway_order_id = str(order_id)
        payment.gateway_txn_id = str(txn_id or '')
        if not success:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=['status', 'gateway_txn_id', 'gateway_order_id'])
            return payment

        amount = (Decimal(str(amount_cents)) / 100).quantize(Decimal('0.01'))
        if amount != payment.amount:
            logger.warning('Paymob order %s paid %s EGP, expected %s EGP', order_id, amount, payment.amount)
            payment.amount = amount
        if invoice.paid_amount() + amount > invoice.total_amount or invoice.status == Invoice.Status.CANCELLED:
            # The money was taken, so it must be recorded; the difference needs a manual refund.
            logger.error('Invoice %s is overpaid (or cancelled) after online payment %s; refund the difference.',
                         invoice.invoice_no, payment.receipt_no)
        payment.status = Payment.Status.SUCCEEDED
        payment.paid_at = timezone.now()
        payment.save()  # also recomputes the invoice status
        return payment


def apply_processed_callback(obj):
    """Body `obj` of a verified transaction processed callback."""
    order = obj.get('order') or {}
    return apply_result(
        order_id=order.get('id'), txn_id=obj.get('id'), success=obj.get('success') is True,
        pending=obj.get('pending') is True, amount_cents=obj.get('amount_cents') or 0,
        reference=order.get('merchant_order_id') or obj.get('special_reference'),
    )


def apply_response_callback(params):
    """Query parameters of a verified transaction response (redirect) callback."""
    return apply_result(
        order_id=params.get('order_id') or params.get('order'), txn_id=params.get('id'),
        success=params.get('success') == 'true', pending=params.get('pending') == 'true',
        amount_cents=params.get('amount_cents') or 0,
        reference=params.get('merchant_order_id') or params.get('special_reference'),
    )
