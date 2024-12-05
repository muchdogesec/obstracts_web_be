from django.test import SimpleTestCase
from djstripe.settings import djstripe_settings

from apps.teams.models import Team


class SubscriberModelTest(SimpleTestCase):
    def test_get_subscriber_model(self):
        model = djstripe_settings.get_subscriber_model()
        self.assertEqual(model, Team)
