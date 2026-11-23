"""
Celery application for the project (spec: "Background Services: Celery workers with Redis").

Run a worker and a beat scheduler locally with:
    celery -A config worker -l info
    celery -A config beat -l info
(requires a running Redis instance; see REDIS_URL in Backend/.env.example)
"""
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('liverlink')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
