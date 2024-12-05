from unittest.mock import patch

from django.http import HttpResponse
from django.test import TestCase

from apps.subscriptions.decorators import active_subscription_required
from apps.subscriptions.tests.utils import get_mock_request
from apps.teams.models import Team
from apps.teams.roles import ROLE_ADMIN
from apps.users.models import CustomUser


class SubscriptionGatingTests(TestCase):
    """These tests demonstrate a testing technique using mocks to fake the return value of the
    `Team.has_active_subscription` method. This allows us to test the behavior of the
    view without needing to set up a real subscription. This is advantageous because it
    is faster and simpler to set up, but it only works if the view does not need to
    interrogate the details of the subscription.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create(username="richard@example.com")
        cls.team = Team.objects.create(name="Royals", slug="royals")
        cls.team.members.add(cls.user, through_defaults={"role": ROLE_ADMIN})

    @patch("apps.teams.models.Team.has_active_subscription", return_value=True)
    def test_gated_view_has_active_subscription(self, _):
        request = get_mock_request(self.team, self.user)
        response = mock_gated_view(request, self.team.slug)
        self.assertEqual(response.status_code, 200)

    def test_gated_view_no_active_subscription(self):
        request = get_mock_request(self.team, self.user)
        response = mock_gated_view(request, self.team.slug)
        self.assertEqual(response.status_code, 302)


@active_subscription_required
def mock_gated_view(request, team_slug):
    return HttpResponse()
