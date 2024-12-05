from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.subscriptions.helpers import cancel_subscription
from apps.teams.models import Team


@receiver(post_delete, sender=Team)
def cancel_subscription_on_team_delete(sender, instance: Team, **kwargs):
    if instance.has_active_subscription:
        cancel_subscription(instance.subscription.id)
