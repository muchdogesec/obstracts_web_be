import os
from datetime import timedelta
from celery import Celery
from celery.schedules import crontab


# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "obstracts_web.settings")

app = Celery("obstracts_web")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'poll_data_from_obstract': {
        'task': 'apps.obstracts_api.tasks.feed_polling',
        'schedule': timedelta(minutes=5),
    },
    'sync_feed_updates': {
        'task': 'apps.obstracts_api.tasks.sync_feed_updates',
        'schedule': timedelta(minutes=1),
    },
}
