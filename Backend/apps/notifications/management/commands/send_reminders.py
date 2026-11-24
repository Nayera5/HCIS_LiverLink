"""
python manage.py send_reminders          send every due reminder / alert once
python manage.py send_reminders --loop   keep running, once every REMINDER_CHECK_INTERVAL (Ctrl+C to stop)

Stands in for the Celery beat schedule while Celery is switched off.
"""
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.notifications.tasks import check_due_reminders


class Command(BaseCommand):
    help = 'Send due appointment / follow-up reminders and pending-task alerts.'

    def add_arguments(self, parser):
        parser.add_argument('--loop', action='store_true',
                            help='Repeat every REMINDER_CHECK_INTERVAL until stopped.')

    def handle(self, *args, loop=False, **options):
        interval = settings.REMINDER_CHECK_INTERVAL.total_seconds()
        while True:
            created = check_due_reminders()
            self.stdout.write(self.style.SUCCESS(f'{created} notification(s) sent.'))
            if not loop:
                return
            try:
                time.sleep(interval)
            except KeyboardInterrupt:
                return
