import logging

import stripe
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from djstripe.enums import SubscriptionStatus
from djstripe.models import Subscription, Price
from djstripe.utils import CURRENCY_SIGILS
from djstripe.settings import djstripe_settings

from stripe.api_resources.billing_portal.session import Session as BillingPortalSession
from stripe.api_resources.checkout import Session as CheckoutSession
from stripe.error import InvalidRequestError

from .exceptions import SubscriptionConfigError
from apps.teams.models import Team
from apps.users.models import CustomUser
from apps.web.meta import absolute_url
from apps.utils.billing import get_stripe_module
from apps.subscriptions.models import SubscriptionConfig

log = logging.getLogger("obstracts_web.subscription")


def subscription_is_active(subscription: Subscription) -> bool:
    return subscription.status in [
        SubscriptionStatus.active,
        SubscriptionStatus.trialing,
    ]


def subscription_is_trialing(subscription: Subscription) -> bool:
    return (
        subscription.status == SubscriptionStatus.trialing
        and subscription.trial_end > timezone.now()
    )


def get_friendly_currency_amount(price: Price, currency: str = None):
    # modified from djstripe's version to only include sigil or currency, but not both
    # and handle multiple currencies
    if not currency:
        currency = price.currency
    if currency != price.currency:
        amount = get_price_for_secondary_currency(price, currency)
    elif price.unit_amount_decimal is None:
        return "Unknown"
    else:
        amount = price.unit_amount_decimal
    return get_price_display_with_currency(amount / 100, currency)


def get_price_for_secondary_currency(price: Price, currency: str):
    # we have to hit the Stripe API for this because djstripe doesn't save it.
    stripe_price = get_stripe_module().Price.retrieve(
        price.id, expand=["currency_options"]
    )
    unit_amount_decimal = stripe_price.currency_options[currency]["unit_amount_decimal"]
    return int(float(unit_amount_decimal))


def get_price_display_with_currency(amount: float, currency: str) -> str:
    currency = currency.upper()
    sigil = CURRENCY_SIGILS.get(currency, "")
    if sigil:
        return "{sigil}{amount:.2f}".format(sigil=sigil, amount=amount)
    else:
        return "{amount:.2f} {currency}".format(amount=amount, currency=currency)


def get_subscription_urls(subscription_holder):
    # get URLs for subscription helpers
    url_bases = [
        "subscription_details",
        "create_stripe_portal_session",
        "subscription_demo",
        "subscription_gated_page",
        "metered_billing_demo",
        # checkout urls
        "create_checkout_session",
        "checkout_canceled",
    ]

    def _construct_url(base):
        return reverse(f"subscriptions_team:{base}", args=[subscription_holder.slug])

    return {url_base: _construct_url(url_base) for url_base in url_bases}


def create_stripe_checkout_session(
    subscription_holder: Team, stripe_price_id: str, user: CustomUser
) -> CheckoutSession:
    stripe = get_stripe_module()
    success_url = f"{settings.FRONTEND_BASE_URL}/dashboard/team/{subscription_holder.id}/subscription/confirm"
    cancel_url = f"{settings.FRONTEND_BASE_URL}/dashboard/team/{subscription_holder.id}/subscription/cancel"

    customer_kwargs = {}
    if subscription_holder.customer:
        customer_kwargs["customer"] = subscription_holder.customer.id

    checkout_session = stripe.checkout.Session.create(
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        payment_method_types=["card"],
        mode="subscription",
        client_reference_id=subscription_holder.id,
        line_items=[
            {
                "price": stripe_price_id,
                "quantity": _get_quantity(stripe_price_id, subscription_holder),
            }
        ],
        allow_promotion_codes=True,
        subscription_data={
            "description": str(subscription_holder),
            "metadata": get_checkout_metadata(subscription_holder, user),
        },
        metadata={
            "source": "subscriptions",
        },
        **customer_kwargs,
    )
    return checkout_session


def get_checkout_metadata(subscription_holder: Team, user: CustomUser) -> dict:
    return {
        f"{djstripe_settings.SUBSCRIBER_CUSTOMER_KEY}": subscription_holder.id,
        "team_id": subscription_holder.id,
        "team_slug": subscription_holder.slug,
        "team_name": subscription_holder.name,
        "user_id": user.id,
        "user_email": user.email,
        "user_name": user.get_full_name(),
    }


def _get_quantity(stripe_price_id, subscription_holder):
    """
    Get quantity for a given Stripe price and subscription holder
    """
    price = Price.objects.get(id=stripe_price_id)
    # if it's metered billing we shouldn't pass a quantity
    if price.recurring.get("usage_type", None) == "metered":
        return None
    # otherwise we pass it from the subscription holder
    return subscription_holder.get_quantity()


def create_stripe_portal_session(team: Team) -> BillingPortalSession:
    stripe = get_stripe_module()
    customer_id = team.customer.id

    portal_session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{settings.FRONTEND_BASE_URL}/teams/{team.id}",
    )
    return portal_session


@transaction.atomic
def provision_subscription(
    subscription_holder: Team, subscription_id: str
) -> Subscription:
    stripe = get_stripe_module()
    subscription = stripe.Subscription.retrieve(subscription_id)
    djstripe_subscription = Subscription.sync_from_stripe_data(subscription)
    subscription_holder.subscription = djstripe_subscription
    subscription_holder.save()
    # attach customer if not set
    if not subscription_holder.customer:
        subscription_holder.customer = djstripe_subscription.customer
        subscription_holder.save()
    return djstripe_subscription


def cancel_subscription(subscription_id: str):
    try:
        subscription = get_stripe_module().Subscription.delete(subscription_id)
    except InvalidRequestError as e:
        if e.code != "resource_missing":
            log.error("Error deleting Stripe subscription: %s", e.user_message)
    else:
        Subscription.sync_from_stripe_data(subscription)

def subscribe_team_to_initial_subscription(subscription_holder):
    default_price_id = SubscriptionConfig.get_default_price_id()
    stripe = get_stripe_module()
    customer = stripe.Customer.create(
        email=subscription_holder.owner.email,
        name=subscription_holder.id,
        metadata={
            'team_id': str(subscription_holder.id),
        }
    )
    customer_id = customer.id
    current_datetime = timezone.now()
    trial_end = current_datetime + SubscriptionConfig.get_trial_duration()
    subscription = stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": default_price_id}],
        trial_end=trial_end,
    )
    djstripe_subscription = Subscription.sync_from_stripe_data(subscription)
    subscription_holder.subscription = djstripe_subscription
    subscription_holder.save()
