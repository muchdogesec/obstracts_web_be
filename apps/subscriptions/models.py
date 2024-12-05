from typing import Optional

from datetime import timedelta
from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from djstripe.enums import SubscriptionStatus
from djstripe.models import Customer, Subscription

from apps.subscriptions.wrappers import SubscriptionWrapper
from .utils import close_customer_and_subscriptions


class SubscriptionModelBase(models.Model):
    """
    Helper class to be used with Stripe Subscriptions.

    Assumes that the associated subclass is a django model containing a
    subscription field that is a ForeignKey to a djstripe.Subscription object.
    """

    # subclass should override with appropriate foreign keys as needed
    subscription = models.ForeignKey(
        "djstripe.Subscription",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text=_("The associated Stripe Subscription object, if it exists"),
    )
    customer = models.ForeignKey(
        Customer,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    billing_details_last_changed = models.DateTimeField(
        default=timezone.now,
        help_text=_("Updated every time an event that might trigger billing happens."),
    )
    last_synced_with_stripe = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Used for determining when to next sync with Stripe."),
    )

    class Meta:
        abstract = True

    @cached_property
    def active_stripe_subscription(self) -> Optional[Subscription]:
        from apps.subscriptions.helpers import subscription_is_active

        if self.subscription and subscription_is_active(self.subscription):
            return self.subscription
        return None

    @cached_property
    def wrapped_subscription(self) -> Optional[SubscriptionWrapper]:
        """
        Returns the current subscription as a SubscriptionWrapper
        """
        if self.subscription:
            return SubscriptionWrapper(self.subscription)
        return None

    def clear_cached_subscription(self):
        """
        Clear the cached subscription object (in case it has changed since the model was created)
        """
        try:
            del self.active_stripe_subscription
        except AttributeError:
            pass
        try:
            del self.wrapped_subscription
        except AttributeError:
            pass

    def has_active_subscription(self) -> bool:
        return self.active_stripe_subscription is not None

    @classmethod
    def get_items_needing_sync(cls):
        return cls.objects.filter(
            Q(last_synced_with_stripe__isnull=True)
            | Q(last_synced_with_stripe__lt=F("billing_details_last_changed")),
            subscription__status=SubscriptionStatus.active,
        )

    def get_quantity(self) -> int:
        # if you use "per-seat" billing, override this accordingly
        return 1

    def close_customer_and_subscriptions(self):
        return close_customer_and_subscriptions(self.subscription.customer.id)


class SubscriptionConfig(models.Model):
    key = models.CharField(max_length=50, unique=True)
    value = models.CharField(max_length=50)

    @staticmethod
    def get_trial_duration():
        data_dict = {}
        for item in SubscriptionConfig.objects.all():
            data_dict[item.key] = item.value
        return timedelta(
            days=int(data_dict.get('subscription_trial_duration_days', 0)),
            hours=int(data_dict.get('subscription_trial_duration_hours', 0)),
            minutes=int(data_dict.get('subscription_trial_duration_minutes', 0)),
        )
