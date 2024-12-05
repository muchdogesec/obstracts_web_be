import typing

from django.http import HttpRequest
from rest_framework.permissions import IsAuthenticated
from rest_framework_api_key.permissions import BaseHasAPIKey

from apps.obstracts_api.models import FeedSubsription
from .helpers import get_user_from_request, get_team_from_request
from .models import UserAPIKey, TeamApiKey


class HasUserAPIKey(BaseHasAPIKey):
    model = UserAPIKey

    def has_permission(self, request: HttpRequest, view: typing.Any) -> bool:
        has_perm = super().has_permission(request, view)
        if has_perm:
            # if they have permission, also populate the request.user object for convenience
            request.user = get_user_from_request(request)
        return has_perm


class HasTeamFeedApiKey(BaseHasAPIKey):
    model = TeamApiKey

    def has_permission(self, request: HttpRequest, view: typing.Any) -> bool:
        has_perm = super().has_permission(request, view)
        if has_perm:
            feed_id = view.kwargs.get('feed_id')
            team = get_team_from_request(request)
            request.team = team
            feed_subscription = FeedSubsription.objects.filter(feed_id=feed_id, team_id=team.id).select_related('feed').first()
            if not feed_subscription:
                return False
            view.feed_id = feed_subscription.feed_id
            return True
        return has_perm

class HasTeamApiKey(BaseHasAPIKey):
    model = TeamApiKey

    def has_permission(self, request: HttpRequest, view: typing.Any) -> bool:
        has_perm = super().has_permission(request, view)
        if has_perm:
            team = get_team_from_request(request)
            view.team = team
            request.team = team
            return True
        return has_perm
# hybrid permission class that can check for API keys or authentication
IsAuthenticatedOrHasUserAPIKey = IsAuthenticated | HasUserAPIKey
