"""Lab business logic, shared by the REST API and (later) the HL7 ORU handler.

Side effects: notifications (results ready / released) and the automatic invoice once an
order is fully resulted.
"""
from django.db import transaction
from django.utils import timezone

from .models import LabOrder, LabResult


class LabError(Exception):
    """A rule violation that should be reported to the caller as a 400."""


@transaction.atomic
def create_order(patient, staff, tests, priority=LabOrder.Priority.ROUTINE):
    order = LabOrder.objects.create(patient=patient, ordered_by=staff, priority=priority)
    LabResult.objects.bulk_create([LabResult(lab_order=order, lab_test=t) for t in tests])
    return order


@transaction.atomic
def record_result(result, value, result_time=None):
    """Fill a pending result: store the value, set the flag from the normal range, update the order."""
    order = result.lab_order
    if order.status == LabOrder.Status.CANCELLED:
        raise LabError('This order was cancelled.')
    result.value = value
    result.flag = result.lab_test.compute_flag(value)
    result.result_time = result_time or timezone.now()
    result.save(update_fields=['value', 'flag', 'result_time'])
    was_resulted = order.status == LabOrder.Status.RESULTED
    order.refresh_status()
    if order.status == LabOrder.Status.RESULTED and not was_resulted:
        _on_order_resulted(order)
    return result


def _on_order_resulted(order):
    """All tests have values: tell the ordering doctor (module 14) and bill the tests (module 13)."""
    from apps.billing.services import invoice_for_lab_order
    from apps.notifications import events

    events.lab_order_resulted(order)
    invoice_for_lab_order(order)


@transaction.atomic
def cancel_order(order):
    if order.status in (LabOrder.Status.RESULTED, LabOrder.Status.CANCELLED):
        raise LabError(f'A {order.get_status_display().lower()} order cannot be cancelled.')
    order.status = LabOrder.Status.CANCELLED
    order.save(update_fields=['status'])
    return order


@transaction.atomic
def release_order(order):
    """The doctor releases all resulted tests of an order to the patient portal."""
    if order.status == LabOrder.Status.CANCELLED:
        raise LabError('A cancelled order cannot be released.')
    if not order.results.filter(value__isnull=False).exists():
        raise LabError('There are no results to release yet.')
    released = order.results.filter(value__isnull=False, is_released=False).update(is_released=True)
    if released:
        from apps.notifications import events

        events.lab_results_released(order)
    return released


def trend_points(patient, test_code, released_only=False):
    qs = LabResult.objects.filter(lab_order__patient=patient, lab_test__code=test_code, value__isnull=False)
    qs = qs.exclude(lab_order__status=LabOrder.Status.CANCELLED)
    if released_only:
        qs = qs.filter(is_released=True)
    return qs.order_by('result_time', 'id')
