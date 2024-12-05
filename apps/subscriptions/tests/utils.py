import datetime
import uuid

from dateutil.relativedelta import relativedelta
from django.contrib.messages.storage import default_storage
from django.contrib.sessions.backends.file import SessionStore
from django.test import RequestFactory
from djstripe import enums
from djstripe.models import (
    Customer,
    Plan,
    Price,
    Product,
    Subscription,
    SubscriptionItem,
)

from apps.subscriptions.metadata import ProductMetadata
from apps.teams.models import Team


def create_subscription_for_team(
    subscription_holder: Team, product: ProductMetadata, metered=False
):
    """Create a dummy subscription for the given product."""
    stripe_product = create_stripe_product(product, metered=metered)

    customer = create_customer()
    subscription = create_subscription(customer, stripe_product)

    subscription_holder.subscription = subscription
    subscription_holder.customer = customer
    subscription_holder.save(update_fields=["subscription", "customer"])

    return subscription


def create_subscription(customer, product):
    subscription = Subscription.objects.create(
        id=_make_stripe_id("subscription"),
        collection_method=enums.InvoiceCollectionMethod.charge_automatically,
        livemode=False,
        status=enums.SubscriptionStatus.active,
        current_period_start=datetime.datetime.utcnow() - relativedelta(months=1),
        current_period_end=datetime.datetime.utcnow() + relativedelta(months=1),
        customer=customer,
    )
    plan = Plan.objects.create(
        id=_make_stripe_id("plan"),
        currency="usd",
        active=True,
        livemode=False,
        interval=enums.PlanInterval.month,
        product=product,
    )
    SubscriptionItem.objects.create(
        id=_make_stripe_id("sub_item"),
        price=product.default_price,
        subscription=subscription,
        livemode=False,
        plan=plan,
    )
    return subscription


def create_customer():
    customer = Customer.objects.create(
        id=_make_stripe_id("customer"),
        livemode=False,
    )
    return customer


def create_stripe_product(product_meta: ProductMetadata, metered=False):
    """Create stripe products. This assumes that all products
    are 'monthly recurring' subscriptions which should be sufficient for tests.
    """
    product = Product.objects.create(
        id=product_meta.stripe_id,
        name=product_meta.name,
        description=product_meta.description,
        livemode=False,
        type=enums.ProductType.service,
        active=True,
    )

    recurring = {
        "meter": _make_stripe_id("meter") if metered else None,
        "interval": "month",
        "usage_type": "metered" if metered else "licensed",
        "interval_count": 1,
        "aggregate_usage": None,
        "trial_period_days": None,
    }

    price = Price.objects.create(
        id=_make_stripe_id("price"),
        type=enums.PriceType.recurring,
        currency="usd",
        unit_amount=100,
        livemode=False,
        product=product,
        active=True,
        recurring=recurring,
    )
    product.default_price = price
    product.save(update_fields=["default_price"])
    return product


def _make_stripe_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex}"


def get_mock_request(team, user):
    """
    Simulates a request object which can be passed directly to a mock view, with a team and logged-in user.
    """
    request = RequestFactory().get("/mock_view")
    request.user = user  # django.contrib.auth.middleware.AuthenticationMiddleware
    request.team = team  # apps.teams.middleware.TeamsMiddleware
    request.session = (
        SessionStore()
    )  # django.contrib.sessions.middleware.SessionMiddleware
    request._messages = default_storage(
        request
    )  # django.contrib.messages.middleware.MessageMiddleware
    return request
