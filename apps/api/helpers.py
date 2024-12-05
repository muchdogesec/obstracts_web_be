from typing import Optional
from django.utils import timezone
from django.http import HttpRequest
from rest_framework_api_key.permissions import KeyParser
from rest_framework.exceptions import PermissionDenied

from apps.api.models import UserAPIKey, TeamApiKey, TeamApiKeyStatus
from apps.users.models import CustomUser


def get_user_from_request(request: HttpRequest) -> Optional[CustomUser]:
    if request is None:
        return None
    if request.user.is_anonymous:
        user_api_key = _get_api_key_object(request, UserAPIKey)
        return user_api_key.user
    else:
        return request.user

def get_team_from_request(request: HttpRequest):
    if request is None:
        return None
    team_api_key = _get_api_key_object(request, TeamApiKey)
    if team_api_key.status != TeamApiKeyStatus.ACTIVE:
        raise PermissionDenied("Invalid key")
    team_api_key.last_used = timezone.now()
    team_api_key.save()
    return team_api_key.team

def _get_api_key_object(request, model_class):
    return model_class.objects.get_from_key(_get_api_key(request))


def _get_api_key(request):
    # inspired by / copied from BaseHasAPIKey.get_key()
    # loosely based on this issue: https://github.com/florimondmanca/djangorestframework-api-key/issues/98
    return KeyParser().get(request)
