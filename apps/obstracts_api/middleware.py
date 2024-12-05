from django.utils.deprecation import MiddlewareMixin
from rest_framework.exceptions import PermissionDenied
from django.utils.functional import SimpleLazyObject

from apps.teams.helpers import get_team_for_request
from apps.teams.models import Membership
from .models import TeamApiKey, FeedSubsription


def _get_team(request, view_kwargs):
    if not hasattr(request, "_cached_team"):
        team = get_team_for_request(request, view_kwargs)
        if team:
            request.session["team"] = str(team.id)
        request._cached_team = team
    return request._cached_team


def _get_team_membership(request):
    if not hasattr(request, "_cached_team_membership"):
        team_membership = None
        if request.user.is_authenticated and request.team:
            try:
                team_membership = Membership.objects.get(
                    team=request.team, user=request.user
                )
            except Membership.DoesNotExist:
                pass
        request._cached_team_membership = team_membership
    return request._cached_team_membership

def has_team_api_permission(request, view_kwargs):
    def _has_team_api_permission():
        api_key = request.headers.get('API-KEY')
        team_id = request.headers.get('team_id')
        feed_id = view_kwargs.get('team_id')

        if not api_key or not team_id:
            raise PermissionDenied()
        if not TeamApiKey.objects.filter(team_id=team_id, api_key=api_key).exists():
            raise PermissionDenied()
        if not FeedSubsription.objects.filter(team_id=team_id, feed_id=feed_id).exists():
            raise PermissionDenied()
        return True
    return _has_team_api_permission()


class TeamsMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        request.has_team_api_permission = has_team_api_permission(request, view_kwargs)
