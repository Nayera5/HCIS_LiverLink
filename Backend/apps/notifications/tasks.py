"""
Celery tasks for Notifications. Registered in config/settings.py CELERY_BEAT_SCHEDULE.

`check_due_reminders` is a stub: the spec's appointment and follow-up reminders need the
Appointment and FollowUpVisit models (apps.scheduling / apps.transplant), which don't exist yet.
Once they do, this task is where their due-reminder queries and notify() calls belong.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def check_due_reminders():
    """Periodic beat task (see CELERY_BEAT_SCHEDULE). Currently a no-op: no source data exists yet."""
    logger.info('check_due_reminders: no scheduling/follow-up models exist yet, nothing to check.')
    return 0
