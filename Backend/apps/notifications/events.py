"""
Notification events (spec §14): one function per thing that happens in another module. The other
modules call these; this file only reads attributes of the objects it is given, so it needs no
imports from them (no import cycles).

Each function creates its notifications in the caller's transaction, so they disappear if that
change is rolled back.
"""
import logging

from django.utils import timezone

from .models import Notification, already_notified, notify

logger = logging.getLogger(__name__)

T = Notification.Type


def _when(value):
    return timezone.localtime(value).strftime('%d %b %Y at %H:%M')


def _staff_user(staff):
    return staff.user if staff is not None else None


def _coordinator_users(case):
    """The case's coordinator, or every active transplant coordinator when none is assigned."""
    if case.coordinator_id:
        return [case.coordinator.user]
    from apps.accounts.models import Staff  # accounts is the base app; local import keeps this module light
    return [staff.user for staff in Staff.objects.select_related('user').filter(
        job_title=Staff.JobTitle.TRANSPLANT_COORDINATOR, user__is_active=True)]


# --------------------------------------------------------------------------- results (labs)

def lab_order_resulted(order):
    """Every test of the order has a value: tell the doctor who ordered it."""
    critical = order.results.filter(flag='critical').count()
    patient = order.patient
    message = f'All results of lab order #{order.pk} for {patient.full_name} (MRN {patient.mrn}) are in.'
    if critical:
        message += f' {critical} result{"s are" if critical != 1 else " is"} critical.'
    notify(_staff_user(order.ordered_by), T.RESULT_READY, message,
           title='Critical lab results' if critical else 'Lab results ready', related=order)


def lab_results_released(order):
    """The doctor released results to the portal: tell the patient."""
    notify(order.patient.user, T.RESULT_READY,
           f'Your results for lab order #{order.pk} are ready. You can view them in your portal.',
           title='Your lab results are ready', related=order)


# --------------------------------------------------------------------------- transplant case stage

def case_stage_changed(case, old_status):
    """A transplant case moved to a new stage: tell the recipient, the coordinator and the referring doctor."""
    new_label = case.get_status_display()
    old_label = type(case).Status(old_status).label if old_status else ''
    staff_message = (f'Transplant case #{case.pk} for {case.recipient.full_name} '
                     f'moved from {old_label} to {new_label}.')
    title = f'Case #{case.pk}: {new_label}'

    staff_users = {user.pk: user for user in
                   [_staff_user(case.referred_by), *_coordinator_users(case)] if user is not None}
    for user in staff_users.values():
        notify(user, T.CASE_UPDATE, staff_message, title=title, related=case)

    notify(case.recipient.user, T.CASE_UPDATE,
           f'Your transplant case is now at the "{new_label}" stage.',
           title='Your transplant case was updated', related=case)


# --------------------------------------------------------------------------- reminders (periodic task)

def appointment_reminder(appointment):
    """Returns True when a reminder was created (False if already sent or nobody to tell)."""
    user = appointment.patient.user
    if user is None or already_notified(user, T.APPOINTMENT_REMINDER, appointment):
        return False
    if appointment.imaging_order_id:  # a scan has no doctor
        notify(user, T.APPOINTMENT_REMINDER, _scan_reminder(appointment.imaging_order, appointment),
               title='Upcoming scan', related=appointment)
        return True
    doctor = appointment.staff.user.get_full_name() or appointment.staff.user.username
    notify(user, T.APPOINTMENT_REMINDER,
           f'Reminder: your {appointment.get_appointment_type_display().lower()} appointment with '
           f'Dr. {doctor} is on {_when(appointment.start_time)}.',
           title='Upcoming appointment', related=appointment)
    return True


# --------------------------------------------------------------------------- imaging orders (module 7)

def _scan_reminder(order, appointment):
    scan = order.billing_service.name
    if appointment is None:
        return f'Please choose an appointment for your scan ({scan}, imaging order #{order.pk}) in your portal.'
    message = f'Reminder: your scan appointment ({scan}) is on {_when(appointment.start_time)}.'
    if order.status == 'ordered':
        message += ' It is waiting for confirmation by the radiology department.'
    return message


def imaging_notice(order, title, message):
    """Tell the patient about their imaging order (nothing happens without a portal account)."""
    return notify(order.patient.user, T.APPOINTMENT_REMINDER, message, title=title, related=order)


def imaging_order_created(order):
    imaging_notice(order, 'Scan requested',
                   f'Your doctor requested a scan: {order.billing_service.name} (imaging order #{order.pk}). '
                   'Please choose an appointment in your portal.')


def imaging_booking_confirmed(order, appointment):
    imaging_notice(order, 'Scan appointment confirmed',
                   f'Your scan ({order.billing_service.name}) is confirmed for {_when(appointment.start_time)}.')


def imaging_booking_cancelled(order):
    imaging_notice(order, 'Scan appointment cancelled',
                   f'Your scan appointment ({order.billing_service.name}) was cancelled. '
                   'Please choose another time in your portal.')


def imaging_order_cancelled(order):
    imaging_notice(order, 'Scan request cancelled',
                   f'Your scan request ({order.billing_service.name}, imaging order #{order.pk}) was cancelled.')


def imaging_coordinator_reminder(order, appointment):
    """Reminder sent by the coordinator. False when the patient already heard about this order today."""
    start_of_day = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    if already_notified(order.patient.user, T.APPOINTMENT_REMINDER, order, since=start_of_day):
        return False
    imaging_notice(order, 'Scan reminder', _scan_reminder(order, appointment))
    return True


# --------------------------------------------------------------------------- follow-up reminders

def follow_up_reminder(visit):
    """Returns True when a reminder was created (False if already sent or nobody to tell)."""
    user = visit.plan.patient.user
    if user is None or already_notified(user, T.FOLLOW_UP_REMINDER, visit):
        return False
    message = f'Reminder: your post-transplant follow-up visit is due on {visit.due_date:%d %b %Y}.'
    if visit.appointment_id:
        message = (f'Reminder: your post-transplant follow-up visit is booked for '
                   f'{_when(visit.appointment.start_time)}.')
    elif visit.due_date >= timezone.localdate():
        message += ' Please book an appointment if you have not done so.'
    notify(user, T.FOLLOW_UP_REMINDER, message, title='Follow-up visit due', related=visit)
    return True


def pending_tasks(case, items, *, since):
    """
    Tell the coordinator(s) which required checklist items (tests, documents...) are still pending.
    Skips anyone already alerted about this case since `since`. Returns how many alerts were created.
    """
    names = [item.item_name for item in items]
    shown = ', '.join(names[:5]) + (f' and {len(names) - 5} more' if len(names) > 5 else '')
    message = (f'Transplant case #{case.pk} for {case.recipient.full_name} has {len(names)} pending '
               f'required item{"s" if len(names) != 1 else ""}: {shown}.')
    created = 0
    for user in _coordinator_users(case):
        if already_notified(user, T.PENDING_TASK, case, since=since):
            continue
        if notify(user, T.PENDING_TASK, message, title=f'Case #{case.pk}: missing items', related=case):
            created += 1
    return created
