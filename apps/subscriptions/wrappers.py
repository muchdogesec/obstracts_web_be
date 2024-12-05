from typing import List

from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from djstripe.models import Price, Product, Subscription
from djstripe.utils import convert_tstamp
from stripe.api_resources.invoice import Invoice
from stripe.error import InvalidRequestError

from apps.utils.billing import get_stripe_module


class SubscriptionWrapper:
    """
    A Wrapper Class for the dj-stripe Subscription object, so that complex functionality can be encapsulated
     in a single place for helper code.
    """

    def __init__(self, subscription: Subscription):
        self.subscription = subscription

    def __getattr__(self, item):
        # pass all calls through to the subscription object
        return getattr(self.subscription, item)

    @property
    def prices(self) -> List[Price]:
        return [item.price for item in self.items.all()]

    @property
    def products(self) -> List[Product]:
        return [price.product for price in self.prices]

    @property
    def is_metered(self) -> bool:
        """
        True if any of the underlying products are metered.
        """
        return self.items.filter(price__recurring__usage_type="metered").exists()

    @property
    def is_trialing(self) -> bool:
        from apps.subscriptions.helpers import subscription_is_trialing

        return subscription_is_trialing(self.subscription)

    @property
    def has_multiple_products(self) -> bool:
        return self.items.count() > 1

    @property
    def display_name(self):
        if self.has_multiple_products:
            return _("Multiple Products")
        else:
            return self.items[0].price.product.name

    @property
    def billing_interval(self):
        # if a subscription has multiple prices the billing interval is required to be the same for all
        # so we can just use the first one.
        price = self.items[0].price
        if price.recurring["interval_count"] == 1:
            return _("Every {interval}").format(interval=price.recurring["interval"])
        else:
            return _("Every {count} {interval}s").format(
                count=price.recurring["interval_count"],
                interval=price.recurring["interval"],
            )

    @cached_property
    def items(self):
        return self.subscription.items.select_related("price__product")

    @cached_property
    def currency(self):
        # dj-stripe doesn't have this so we have to hit the API
        # should remove this once this issue is resolved: https://github.com/dj-stripe/dj-stripe/issues/1975
        try:
            stripe_subscription = get_stripe_module().Subscription.retrieve(
                self.subscription.id
            )
            return stripe_subscription.currency
        except InvalidRequestError:
            return None

    def uses_secondary_currency(self):
        return any([p.currency != self.currency for p in self.prices])


class InvoiceFacade:
    """
    A helper class to provide some convenience properties on invoices for the front end.
    """

    def __init__(self, invoice: Invoice):
        self.invoice = invoice

    @property
    def total_display(self):
        from apps.subscriptions.helpers import get_price_display_with_currency

        return get_price_display_with_currency(
            (self.invoice.total / 100), self.invoice.currency
        )

    @property
    def period_end(self):
        return convert_tstamp(self.invoice.period_end).date()
