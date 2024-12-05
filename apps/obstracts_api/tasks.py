from datetime import timedelta
from django.utils import timezone
from celery import shared_task
from .models import Feed
from .utils import init_reload_feed, get_obstracts_job, get_obstracts_feed


@shared_task()
def reload_feed(feed_id):
    print(feed_id, "started")
    feed = Feed.objects.get(id=feed_id)
    job_data = init_reload_feed(feed.profile_id, feed.obstract_feed_metadata["id"])
    print(job_data)
    feed.polling = False
    feed.job_metadata = job_data
    feed.active_job_id = feed.job_metadata['id']
    feed.next_polling_time = timezone.now() + timedelta(
        minutes=feed.polling_schedule_minute
    )
    feed.obstract_feed_metadata = get_obstracts_feed(feed_id)
    feed.save()
    print(feed_id, "ended")


@shared_task()
def feed_polling():
    now = timezone.now()
    feeds = (
        Feed.objects.exclude(next_polling_time__gt=now)
        .filter(polling=False)
        .filter(polling_schedule_minute__gt=0)
    )
    for feed in feeds:
        reload_feed.delay(feed.id)
    feed_ids = [feed.id for feed in feeds]
    Feed.objects.filter(id__in=feed_ids).update(polling=True)


@shared_task()
def update_feed(feed_id):
    feed = Feed.objects.get(id=feed_id)
    job = get_obstracts_job(feed_id, feed.job_metadata["id"])
    feed.job_metadata = job
    feed.obstract_feed_metadata = get_obstracts_feed(feed_id)
    if job["state"] in ["processed", "processing_failed", "retrieve_failed"]:
        feed.active_job_id = None
    feed.save()


@shared_task()
def sync_feed_updates():
    feeds = Feed.objects.exclude(active_job_id=None)
    for feed in feeds:
        update_feed.delay(feed.id)
