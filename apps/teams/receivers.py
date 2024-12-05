from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from djstripe import signals as djstripe_signals
from djstripe.enums import SubscriptionStatus
from djstripe.models import Subscription, Product
from apps.api.models import TeamApiKey, TeamApiKeyStatus
from apps.subscriptions.helpers import subscription_is_active
from .cache import save_product_allowed_feeds_value, get_product_allowed_feeds_value
from .models import Membership, Team
from .utils import update_user_teams_on_auth0


@receiver(post_save, sender=Membership)
def membership_created_or_updated(sender, instance, created, **kwargs):
    if not created:
        return
    update_user_teams_on_auth0(instance.user_id)


@receiver(post_delete, sender=Membership)
def membership_deleted(sender, instance, **kwargs):
    update_user_teams_on_auth0(instance.user_id)

@receiver(pre_save, sender=Subscription)
def handle_subscription_pre_save(sender, signal, instance, **kwargs):
    old_instance = Subscription.objects.filter(id=instance.id).first()
    if not subscription_is_active(instance):
        TeamApiKey.objects.filter(team__subscription__djstripe_id=instance.djstripe_id).update(status=TeamApiKeyStatus.BLOCKED)
        return
    if not old_instance:
        return
    old_allowed_api_access = old_instance.plan.product.metadata.get('allowed_api_access')
    new_allowed_api_access = instance.plan.product.metadata.get('allowed_api_access')
    if new_allowed_api_access == 'true':
        return
    if old_allowed_api_access == new_allowed_api_access:
        return
    TeamApiKey.objects.filter(team__subscription__djstripe_id=instance.djstripe_id).update(status=TeamApiKeyStatus.BLOCKED)

@receiver(pre_save, sender=Product)
def handle_product_pre_save(sender, signal, instance, **kwargs):
    old_product = Product.objects.get(id=instance.id)
    save_product_allowed_feeds_value(old_product.id, old_product.metadata.get('allowed_api_access'))

@receiver(post_save, sender=Product)
def handle_product_post_save(sender, signal, instance, **kwargs):
    if instance.metadata.get('allowed_api_access') == 'true':
        return
    old_value = get_product_allowed_feeds_value(instance.id)
    allowed_api_access = instance.metadata.get('allowed_api_access')
    if allowed_api_access == 'true':
        return
    if old_value == allowed_api_access:
        return
    active_subscriptions = Subscription.objects.filter(status=SubscriptionStatus.active, plan__product__id=instance.id)
    active_subscriptions_ids = [subscription.djstripe_id for subscription in active_subscriptions]
    TeamApiKey.objects.filter(team__subscription_id__in=active_subscriptions_ids).update(status=TeamApiKeyStatus.BLOCKED)
