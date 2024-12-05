from unittest import mock

from django.http import HttpResponse
from django.test import TestCase

from apps.subscriptions.decorators import active_subscription_required
from apps.subscriptions.metadata import ProductMetadata
from apps.subscriptions.tests.utils import (
    get_mock_request,
    create_subscription_for_team,
)
from apps.teams.models import Team
from apps.teams.roles import ROLE_ADMIN
from apps.users.models import CustomUser

PASSWORD = "123"

MOCK_ACTIVE_PRODUCTS = [
    ProductMetadata(
        stripe_id="prod_abc",
        slug="plan-a",
        name="Plan A",
        features=[],
        price_displays={},
        description="This is Plan A",
        is_default=False,
    ),
    ProductMetadata(
        stripe_id="prod_def",
        slug="plan-b",
        name="Plan B",
        features=[],
        price_displays={},
        description="This is Plan B",
        is_default=False,
    ),
]


@mock.patch("apps.subscriptions.metadata.ACTIVE_PRODUCTS", MOCK_ACTIVE_PRODUCTS)
class SubscriptionTests(TestCase):
    """These tests demonstrate how to test subscription gated views by creating the subscription
    (and related objects) in the database. This is useful if some aspect of the test relies on the details
    of the subscription e.g. specific features to enable etc.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user_with_sub = CustomUser.objects.create(username="richard@example.com")
        cls.user_without_sub = CustomUser.objects.create(username="robin@example.com")

        cls.team_with_sub = Team.objects.create(name="Royals", slug="royals")
        cls.team_with_sub.members.add(
            cls.user_with_sub, through_defaults={"role": ROLE_ADMIN}
        )

        cls.team_without_sub = Team.objects.create(name="Bandits", slug="bandits")
        cls.team_without_sub.members.add(
            cls.user_without_sub, through_defaults={"role": ROLE_ADMIN}
        )

        cls.subscription = create_subscription_for_team(
            cls.team_with_sub, MOCK_ACTIVE_PRODUCTS[0], metered=True
        )

    def test_gated_view_has_active_subscription(self):
        request = get_mock_request(self.team_with_sub, self.user_with_sub)
        response = mock_gated_view(request, self.team_with_sub.slug)
        self.assertEqual(response.status_code, 200)

    def test_gated_view_no_active_subscription(self):
        request = get_mock_request(self.team_without_sub, self.user_without_sub)
        response = mock_gated_view(request, self.team_without_sub.slug)
        self.assertEqual(response.status_code, 302)

    def test_gated_view_limit_to_plan_allow(self):
        """The subscription has access to this view because it is on to the correct plan."""
        request = get_mock_request(self.team_with_sub, self.user_with_sub)
        response = mock_view_limited_to_plan_a(request, self.team_with_sub.slug)
        self.assertEqual(response.status_code, 200)

    def test_gated_view_limit_to_plan_deny(self):
        """The subscription does not have access to this view because it is limited to a different plan."""
        request = get_mock_request(self.team_with_sub, self.user_with_sub)
        response = mock_view_limited_to_plan_b(request, self.team_with_sub.slug)
        self.assertEqual(response.status_code, 302)


@active_subscription_required
def mock_gated_view(request, team_slug):
    return HttpResponse()


@active_subscription_required(limit_to_plans=["plan-a"])
def mock_view_limited_to_plan_a(request, team_slug):
    return HttpResponse()


@active_subscription_required(limit_to_plans=["plan-b"])
def mock_view_limited_to_plan_b(request, team_slug):
    return HttpResponse()
