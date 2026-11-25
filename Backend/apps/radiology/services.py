"""
Imaging booking rules. Every change of a scan appointment goes through here, so the order, the
appointment and the slot always agree:

    book    slot chosen by the patient     -> order 'scheduled' (confirmed)
            slot chosen by the radiologist -> order 'scheduled' (confirmed)
    confirm                                -> order 'scheduled'
    release (cancelled or no-show)         -> order back to 'ordered', slot free again
    acquire                                -> order 'acquired', appointment completed
    cancel the order                       -> appointment cancelled, slot free again

Call inside transaction.atomic() with the order locked (views.lock_order). Locks are always taken in
the order: imaging order, slot, appointment.
"""
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.audit import audit
from apps.accounts.models import AuditLog
from apps.notifications import events
from apps.scheduling.models import Appointment

from .models import ImagingOrder, ImagingSlot

A = AuditLog.Action
S = ImagingOrder.Status
V = Appointment.Status
ORDER, APPOINTMENT = "radiology.imagingorder", "scheduling.appointment"

TAKEN = "This scan slot is no longer available. Choose another one."


def slot_bookings(**filters):
    return Appointment.objects.filter(status__in=Appointment.SLOT_HOLDING_STATUSES, **filters)


def available_slots(order):
    """Published, free, future slots for the ordered service."""
    return ImagingSlot.objects.filter(
        ~Exists(slot_bookings(imaging_slot=OuterRef("pk"))),
        billing_service_id=order.billing_service_id, is_published=True, start_time__gt=timezone.now())


def active_booking(order, lock=True):
    """The order's booked / checked-in appointment, or None."""
    qs = Appointment.objects.select_for_update() if lock else Appointment.objects
    return qs.filter(imaging_order=order, status__in=Appointment.ACTIVE_STATUSES).first()


def set_order_status(request, order, new_status, reason=""):
    if order.status == new_status:
        return
    changes = {"status": {"from": order.status, "to": new_status}}
    order.status = new_status
    order.save(update_fields=["status"])
    audit(request, A.STATUS_CHANGE, ORDER, entity_id=order.pk, patient=order.patient, changes=changes, reason=reason)


def _set_appointment_status(request, appointment, new_status, reason=""):
    changes = {"status": {"from": appointment.status, "to": new_status}}
    appointment.status = new_status
    appointment.save(update_fields=["status"])
    audit(request, A.STATUS_CHANGE, APPOINTMENT, entity_id=appointment.pk, patient=appointment.patient,
          changes=changes, reason=reason)


def check_patient_may_change(appointment):
    if appointment and (appointment.status != V.BOOKED or appointment.start_time <= timezone.now()):
        raise ValidationError({"detail": "This scan appointment can no longer be changed here. Contact the hospital."})


def book(request, order, slot_id, *, by_patient=False):
    """Book the order's scan in a slot, or move its existing booking there."""
    if order.status not in ImagingOrder.ACTIVE_STATUSES:
        raise ValidationError({"slot": f"This order is {order.get_status_display().lower()}."})
    slot = ImagingSlot.objects.select_for_update().filter(pk=slot_id).first()
    if slot is None or slot.billing_service_id != order.billing_service_id:
        raise ValidationError({"slot": "Choose a scan slot for the ordered imaging type."})
    appointment = active_booking(order)
    if by_patient:
        check_patient_may_change(appointment)
    if appointment and appointment.imaging_slot_id == slot.pk:
        raise ValidationError({"slot": "The scan is already booked in this slot."})
    if appointment and appointment.status != V.BOOKED:
        raise ValidationError({"slot": "The patient has checked in: the booking cannot be moved."})
    if not slot.is_published or slot.start_time <= timezone.now() or slot_bookings(imaging_slot=slot).exists():
        raise ValidationError({"slot": TAKEN})
    overlapping = Appointment.objects.filter(
        patient_id=order.patient_id, status__in=Appointment.ACTIVE_STATUSES,
        start_time__lt=slot.end_time, end_time__gt=slot.start_time)
    if appointment:
        overlapping = overlapping.exclude(pk=appointment.pk)
    if overlapping.exists():
        raise ValidationError({"slot": "The patient has another appointment at this time."})

    try:
        with transaction.atomic():
            if appointment:
                changes = {"imaging_slot": {"from": appointment.imaging_slot_id, "to": slot.pk},
                           "start_time": {"from": appointment.start_time.isoformat(),
                                          "to": slot.start_time.isoformat()}}
                appointment.imaging_slot = slot
                appointment.start_time, appointment.end_time = slot.start_time, slot.end_time
                appointment.save(update_fields=["imaging_slot", "start_time", "end_time"])
                action = A.UPDATE
            else:
                changes = {"imaging_order": {"from": None, "to": order.pk},
                           "imaging_slot": {"from": None, "to": slot.pk}}
                appointment = Appointment.objects.create(
                    patient=order.patient, booked_by=request.user, appointment_type=Appointment.Type.IMAGING,
                    imaging_order=order, imaging_slot=slot, start_time=slot.start_time, end_time=slot.end_time)
                action = A.CREATE
    except IntegrityError:  # the database constraint: someone else took the slot
        raise ValidationError({"slot": TAKEN})
    audit(request, action, APPOINTMENT, entity_id=appointment.pk, patient=order.patient, changes=changes)
    set_order_status(request, order, S.SCHEDULED)
    events.imaging_booking_confirmed(order, appointment)
    return appointment


def confirm(request, order):
    """Radiologist confirms the slot the patient chose."""
    appointment = active_booking(order)
    if appointment is None:
        raise ValidationError({"status": "No scan slot is booked yet: choose a slot for this order."})
    if appointment.start_time <= timezone.now():
        raise ValidationError({"status": "The booked slot has passed: move the booking or record a no-show."})
    set_order_status(request, order, S.SCHEDULED)
    events.imaging_booking_confirmed(order, appointment)


def release(request, order, new_status, *, reason="", by_patient=False):
    """Cancel the booking, or record a no-show. The order goes back to 'ordered' so it can be booked again."""
    appointment = active_booking(order)
    if appointment is None:
        raise ValidationError({"detail": "This order has no active booking."})
    if by_patient:
        check_patient_may_change(appointment)
    if not appointment.can_move_to(new_status):
        raise ValidationError({"detail": f"The appointment is {appointment.get_status_display().lower()}."})
    if new_status == V.NO_SHOW and appointment.start_time > timezone.now():
        raise ValidationError({"detail": "A no-show can only be recorded after the appointment time."})
    _set_appointment_status(request, appointment, new_status, reason)
    set_order_status(request, order, S.ORDERED, reason)
    if new_status == V.CANCELLED and not by_patient:
        events.imaging_booking_cancelled(order)


def acquire(request, order):
    appointment = active_booking(order)
    if appointment:
        if timezone.localdate(appointment.start_time) > timezone.localdate():
            raise ValidationError({"status": "The scan is booked for a later day: move or cancel the booking first."})
        _set_appointment_status(request, appointment, V.COMPLETED)
    set_order_status(request, order, S.ACQUIRED)
    from apps.billing.services import invoice_for_imaging_order
    invoice_for_imaging_order(order, appointment)


def cancel_order(request, order, reason):
    appointment = active_booking(order)
    if appointment:
        _set_appointment_status(request, appointment, V.CANCELLED, reason)
    set_order_status(request, order, S.CANCELLED, reason)
    events.imaging_order_cancelled(order)
