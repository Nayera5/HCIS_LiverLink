"""
Celery tasks for Notifications. Registered in config/settings.py CELERY_BEAT_SCHEDULE (every 15 min).

`check_due_reminders` sends, without duplicates:
- appointment reminders for booked appointments starting in the next 24 hours;
- follow-up reminders for scheduled follow-up visits due in the next 3 days;
- pending-task alerts to the coordinator for open cases with pending required checklist items,
  at most once a day per case.
"""
import datetime
import logging

from celery import shared_task
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from . import events

logger = logging.getLogger(__name__)

APPOINTMENT_REMINDER_WINDOW = datetime.timedelta(hours=24)
FOLLOW_UP_REMINDER_DAYS = 3
# Cases still being worked up; later stages no longer depend on the checklist.
CHECKLIST_STAGES = ('referred', 'under_evaluation')


def send_appointment_reminders(now):
    from apps.scheduling.models import Appointment

    due = Appointment.objects.select_related('patient__user', 'staff__user').filter(
        status=Appointment.Status.BOOKED, start_time__gt=now, start_time__lte=now + APPOINTMENT_REMINDER_WINDOW,
        patient__user__isnull=False,
    )
    return sum(events.appointment_reminder(appointment) for appointment in due)


def send_follow_up_reminders(today):
    from apps.transplant.models import FollowUpVisit

    due = FollowUpVisit.objects.select_related('plan__patient__user', 'appointment').filter(
        status=FollowUpVisit.Status.SCHEDULED, due_date__gte=today,
        due_date__lte=today + datetime.timedelta(days=FOLLOW_UP_REMINDER_DAYS),
        plan__patient__user__isnull=False,
    )
    return sum(events.follow_up_reminder(visit) for visit in due)


def send_pending_task_alerts(now):
    from apps.transplant.models import ChecklistItem, TransplantCase

    pending = ChecklistItem.objects.filter(is_required=True, status=ChecklistItem.Status.PENDING)
    cases = (TransplantCase.objects.select_related('recipient', 'coordinator__user')
             .filter(status__in=CHECKLIST_STAGES, checklist_items__in=pending).distinct()
             .prefetch_related(Prefetch('checklist_items', queryset=pending, to_attr='pending_items')))
    start_of_day = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
    return sum(events.pending_tasks(case, case.pending_items, since=start_of_day) for case in cases)


@shared_task
def check_due_reminders():
    """Periodic beat task. Returns the number of notifications created."""
    now = timezone.now()
    total = 0
    for name, step in (('appointment reminders', lambda: send_appointment_reminders(now)),
                       ('follow-up reminders', lambda: send_follow_up_reminders(timezone.localdate(now))),
                       ('pending-task alerts', lambda: send_pending_task_alerts(now))):
        # One failing step must not stop the others.
        try:
            with transaction.atomic():
                count = step()
        except Exception:
            logger.exception('check_due_reminders: %s failed', name)
            continue
        logger.info('check_due_reminders: %d %s', count, name)
        total += count
    return total
