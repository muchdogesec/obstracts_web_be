from datetime import timedelta
from django.utils import  timezone
from rest_framework import serializers
from .models import Feed
from .utils import create_obstracts_feed, create_obstracts_skeleton_feed, get_obstracts_feed


class FeedSerializer(serializers.Serializer):
    url = serializers.CharField(max_length=255, write_only=True)
    profile_id = serializers.UUIDField()
    include_remote_blogs = serializers.BooleanField(write_only=True)
    is_public = serializers.BooleanField()
    polling_schedule_minute = serializers.IntegerField()
    id = serializers.UUIDField(read_only=True)
    obstract_feed_metadata = serializers.JSONField(read_only=True)
    next_polling_time = serializers.DateTimeField(read_only=True)
    
    pretty_url = serializers.CharField(write_only=True, required=False, allow_blank=True)
    description = serializers.CharField(write_only=True, required=False, allow_blank=True)
    title = serializers.CharField(write_only=True, required=False, allow_blank=True)


    def create(self, *args, **kwargs):
        validated_data = self.validated_data
        job = create_obstracts_feed(
            validated_data["profile_id"],
            validated_data["url"],
            validated_data["include_remote_blogs"],
            validated_data.get("pretty_url"),
            validated_data.get("description"),
            validated_data.get("title"),
        )
        feed_id = job['feed_id']
        feed = get_obstracts_feed(feed_id)
        polling_schedule_minute=validated_data["polling_schedule_minute"]
        return Feed.objects.create(
            id=feed['id'],
            is_public=validated_data["is_public"],
            polling_schedule_minute=polling_schedule_minute,
            obstract_feed_metadata=feed,
            job_metadata=job,
            profile_id=validated_data['profile_id'],
            next_polling_time=timezone.now() + timedelta(minutes=polling_schedule_minute),
            active_job_id=job['id'],
        )

    def update(self, instance, validated_data):
        validated_data = self.validated_data
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        feed_id = instance.obstract_feed_metadata['id']
        feed = get_obstracts_feed(feed_id)
        instance.obstract_feed_metadata = feed
        instance.save()
        return instance


class SkeletonFeedSerializer(serializers.Serializer):
    url = serializers.CharField(max_length=255, write_only=True)    
    pretty_url = serializers.CharField(write_only=True, required=False, allow_blank=True)
    description = serializers.CharField(write_only=True, required=False, allow_blank=True)
    title = serializers.CharField(write_only=True)
    id = serializers.CharField(read_only=True)


    def create(self, *args, **kwargs):
        validated_data = self.validated_data
        feed = create_obstracts_skeleton_feed(
            validated_data["url"],
            validated_data.get("pretty_url"),
            validated_data.get("description"),
            validated_data.get("title"),
        )
        return Feed.objects.create(
            id=feed['id'],
            is_public=True,
            polling_schedule_minute=0,
            obstract_feed_metadata=feed,
            job_metadata={},
            next_polling_time=None,
        )


class FeedWithSubscriptionSerializer(FeedSerializer):
    is_subscribed = serializers.BooleanField()


class SubscribeFeedSerializer(serializers.Serializer):
    feed_id = serializers.CharField()


class SubscribedFeedSerializer(serializers.Serializer):
    profile_id = serializers.UUIDField(source="feed.profile_id")
    id = serializers.UUIDField(source="feed.id")
    obstract_feed_metadata = serializers.DictField(source="feed.obstract_feed_metadata")
    next_polling_time = serializers.DateTimeField(source="feed.next_polling_time")
