import uuid
from django.db import models
from django.conf import settings
from  apps.teams.models import Team
from rest_framework_api_key.models import AbstractAPIKey


# Create your models here.
class Feed(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, unique=True)
    obstract_feed_metadata = models.JSONField()
    profile_id = models.UUIDField(null=True, blank=True)
    is_public = models.BooleanField(default=False)
    polling_schedule_minute = models.IntegerField(default=0)
    job_metadata = models.JSONField()
    next_polling_time = models.DateTimeField(null=True, blank=True)
    polling = models.BooleanField(default=False)
    title = models.CharField(max_length=50, blank=True, null=True)
    active_job_id = models.UUIDField(blank=True, null=True)


class FeedSubsription(models.Model):
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)

