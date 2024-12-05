from django.conf import settings
from django.db import models
from rest_framework_api_key.models import AbstractAPIKey

from apps.teams.models import Team, Membership

class TeamApiKeyStatus:
    BLOCKED = 'blocked'
    ACTIVE = 'active'

class UserAPIKey(AbstractAPIKey):
    """
    API Key associated with a User, allowing you to scope the key's API access based on what the user
    is allowed to view/do.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="api_keys"
    )

    class Meta(AbstractAPIKey.Meta):
        verbose_name = "User API key"
        verbose_name_plural = "User API keys"


class TeamApiKey(AbstractAPIKey):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    status = models.CharField(max_length=10, default=TeamApiKeyStatus.ACTIVE)
    key_id = models.UUIDField(blank=True, null=True)
    last_used = models.DateTimeField(blank=True, null=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE)
    clear_key = models.CharField(max_length=100, blank=True, null=True)
