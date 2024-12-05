import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext
from waffle import get_setting
from waffle.models import AbstractUserFlag, CACHE_EMPTY
from waffle.utils import keyfmt, get_cache

from apps.utils.models import BaseModel
from apps.subscriptions.models import SubscriptionModelBase
from apps.web.meta import absolute_url

from . import roles


class Team(BaseModel, SubscriptionModelBase):
    """
    A Team, with members.
    """

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    slug = models.SlugField(null=True, blank=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="teams", through="Membership"
    )
    feeds = models.ManyToManyField(
        'obstracts_api.Feed', related_name="team", through="obstracts_api.FeedSubsription"
    )
    is_private = models.BooleanField(default=False)

    # your team customizations go here.

    def __str__(self):
        return self.name

    @property
    def email(self):
        return self.membership_set.filter(role=roles.ROLE_ADMIN).first().user.email

    @property
    def sorted_memberships(self):
        return self.membership_set.order_by("user__email")

    def pending_invitations(self):
        return self.invitations.filter(is_accepted=False)

    @property
    def dashboard_url(self) -> str:
        return reverse("web_team:home", args=[self.slug])

    @property
    def has_active_subscription(self):
        return True if self.active_stripe_subscription else False

    def get_user_limit(self):
        if not self.active_stripe_subscription:
            return 0
        return int(self.subscription.plan.product.metadata.get('allowed_user_count', 0))

    @property
    def user_limit(self):
        return self.get_user_limit()

    @property
    def feed_limit(self):
        return self.get_feed_limit()

    @property
    def allowed_api_access(self):
        return self.get_allowed_api_access()


    @property
    def allowed_data_download(self):
        return self.get_allowed_data_download()

    def get_feed_limit(self):
        if not self.active_stripe_subscription:
            return 0
        return int(self.subscription.plan.product.metadata.get('allowed_feed_subscriptions', 0))

    def get_allowed_api_access(self):
        if not self.active_stripe_subscription:
            return False
        return self.subscription.plan.product.metadata.get('allowed_api_access', '') == 'true'

    def get_allowed_data_download(self):
        if not self.active_stripe_subscription:
            return False
        return self.subscription.plan.product.metadata.get('allowed_data_download', '') == 'true'


class Membership(BaseModel):
    """
    A user's team membership
    """

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=100, choices=roles.ROLE_CHOICES)
    # your additional membership fields go here.

    def __str__(self):
        return f"{self.user}: {self.team}"

    def is_admin(self) -> bool:
        return self.role == roles.ROLE_ADMIN

    def is_owner(self) -> bool:
        return self.role == roles.ROLE_OWNER

    class Meta:
        # Ensure a user can only be associated with a team once.
        unique_together = ("team", "user")


class Invitation(BaseModel):
    """
    An invitation for new team members.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    role = models.CharField(
        max_length=100, choices=roles.ROLE_CHOICES, default=roles.ROLE_MEMBER
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
    )
    is_accepted = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accepted_invitations",
        null=True,
        blank=True,
    )

    def get_url(self) -> str:
        link = settings.INVITATION_URL + str(self.id)
        print(link)
        return link


class BaseTeamModel(BaseModel):
    """
    Abstract model for objects that are part of a team.

    See `teams_example` app for usage.
    """

    team = models.ForeignKey(
        Team, verbose_name=gettext("Team"), on_delete=models.CASCADE
    )

    class Meta:
        abstract = True


class Flag(AbstractUserFlag):
    """Custom Waffle flag to support usage with teams.

    See https://waffle.readthedocs.io/en/stable/types/flag.html#custom-flag-models"""

    FLAG_TEAMS_CACHE_KEY = "FLAG_TEAMS_CACHE_KEY"
    FLAG_TEAMS_CACHE_KEY_DEFAULT = "flag:%s:teams"

    teams = models.ManyToManyField(
        Team,
        blank=True,
        help_text=gettext("Activate this flag for these teams."),
    )

    def get_flush_keys(self, flush_keys=None):
        flush_keys = super(Flag, self).get_flush_keys(flush_keys)
        teams_cache_key = get_setting(
            Flag.FLAG_TEAMS_CACHE_KEY, Flag.FLAG_TEAMS_CACHE_KEY_DEFAULT
        )
        flush_keys.append(keyfmt(teams_cache_key, self.name))
        return flush_keys

    def is_active(self, request, read_only=False):
        is_active = super().is_active(request, read_only)
        if is_active:
            return is_active

        if not self.pk:
            # flag not created
            return False

        team = getattr(request, "team")
        if team:
            team_ids = self._get_team_ids()
            return team.pk in team_ids

    def _get_team_ids(self):
        cache = get_cache()
        cache_key = keyfmt(
            get_setting(Flag.FLAG_TEAMS_CACHE_KEY, Flag.FLAG_TEAMS_CACHE_KEY_DEFAULT),
            self.name,
        )
        cached = cache.get(cache_key)
        if cached == CACHE_EMPTY:
            return set()
        if cached:
            return cached

        team_ids = set(self.teams.all().values_list("pk", flat=True))
        cache.add(cache_key, team_ids or CACHE_EMPTY)
        return team_ids


class TeamProfile(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    profile_id = models.UUIDField()
    metadata = models.JSONField()
