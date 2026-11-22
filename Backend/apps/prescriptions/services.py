"""Prescription and treatment-plan business rules, shared by the REST API and (later) HL7/EMR."""
from django.db import transaction
from django.utils import timezone

from .models import Prescription, TreatmentPlan


class RxError(Exception):
    """A rule violation that should be reported to the caller as a 400."""


def _jsonable(value):
    return value.isoformat() if hasattr(value, 'isoformat') else value


def diff(instance, data, fields):
    """{field: {"from": old, "to": new}} for every field in `data` whose value actually changes."""
    changes = {}
    for field in fields:
        if field in data and getattr(instance, field) != data[field]:
            changes[field] = {'from': _jsonable(getattr(instance, field)), 'to': _jsonable(data[field])}
    return changes


# --------------------------------------------------------------------------- prescriptions

@transaction.atomic
def prescribe(patient, staff, drug, **fields):
    if not drug.is_active:
        raise RxError(f'{drug.name} is no longer in the active drug catalog.')
    return Prescription.objects.create(patient=patient, prescribed_by=staff, drug=drug, **fields)


@transaction.atomic
def stop_prescription(rx, reason):
    """Doctor discontinues an active prescription. Returns the audit `changes`."""
    if rx.status != Prescription.Status.ACTIVE:
        raise RxError(f'A {rx.get_status_display().lower()} prescription cannot be stopped.')
    if not (reason or '').strip():
        raise RxError('A reason is required to stop a prescription.')
    changes = {'status': {'from': rx.status, 'to': Prescription.Status.STOPPED}}
    rx.status = Prescription.Status.STOPPED
    rx.stopped_at = timezone.now()
    rx.stop_reason = reason.strip()
    rx.save(update_fields=['status', 'stopped_at', 'stop_reason'])
    return changes


@transaction.atomic
def complete_prescription(rx):
    if rx.status != Prescription.Status.ACTIVE:
        raise RxError(f'A {rx.get_status_display().lower()} prescription cannot be completed.')
    changes = {'status': {'from': rx.status, 'to': Prescription.Status.COMPLETED}}
    rx.status = Prescription.Status.COMPLETED
    rx.save(update_fields=['status'])
    return changes


# --------------------------------------------------------------------------- treatment plans

def _check_dates(start, review):
    if review is not None and start is not None and review < start:
        raise RxError('The review date cannot be before the start date.')


@transaction.atomic
def create_plan(patient, staff, **fields):
    _check_dates(fields.get('start_date'), fields.get('review_date'))
    return TreatmentPlan.objects.create(patient=patient, created_by=staff, **fields)


@transaction.atomic
def update_plan(plan, data):
    """Edit an ACTIVE plan. Returns the changes ({} means nothing changed and nothing was saved)."""
    plan = TreatmentPlan.objects.select_for_update().get(pk=plan.pk)
    if plan.status != TreatmentPlan.Status.ACTIVE:
        raise RxError(f'A {plan.get_status_display().lower()} plan can no longer be edited.')
    changes = diff(plan, data, TreatmentPlan.EDITABLE_FIELDS)
    if not changes:
        return plan, {}
    for field in changes:
        setattr(plan, field, data[field])
    _check_dates(plan.start_date, plan.review_date)
    plan.save()
    return plan, changes


@transaction.atomic
def close_plan(plan, new_status):
    """Mark an active plan completed or cancelled. Returns the audit `changes`."""
    if new_status not in (TreatmentPlan.Status.COMPLETED, TreatmentPlan.Status.CANCELLED):
        raise RxError('Invalid status.')
    if plan.status != TreatmentPlan.Status.ACTIVE:
        raise RxError(f'This plan is already {plan.get_status_display().lower()}.')
    changes = {'status': {'from': plan.status, 'to': new_status}}
    plan.status = new_status
    plan.save(update_fields=['status', 'updated_at'])
    return changes
