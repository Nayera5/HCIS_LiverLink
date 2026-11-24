# Celery is switched off for now (no Redis available). Reminders run without it: see
# apps.notifications.tasks.run_due_reminders_if_due and `manage.py send_reminders`.
# To switch Celery back on, uncomment these lines, config/celery.py and the CELERY_* settings.
# from .celery import app as celery_app
#
# __all__ = ['celery_app']
