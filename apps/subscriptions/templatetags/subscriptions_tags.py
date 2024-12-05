from django import template
from djstripe.models import SubscriptionItem

from apps.subscriptions.helpers import get_friendly_currency_amount

register = template.Library()


@register.simple_tag
def render_subscription_item_price(subscription_item: SubscriptionItem, currency: str):
    if subscription_item.price.currency != currency:
        return get_friendly_currency_amount(subscription_item.price, currency)
    return subscription_item.price.human_readable_price
