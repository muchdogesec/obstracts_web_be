import dataclasses
from typing import List, Optional

from django.utils.translation import gettext as _

from apps.subscriptions.exceptions import (
    FeatureGateError,
    NoSubscriptionFoundError,
    PlanNotSupportedError,
)
from apps.subscriptions.metadata import get_product_with_metadata
from apps.subscriptions.models import SubscriptionModelBase


@dataclasses.dataclass
class FeatureGateCheckResult:
    passed: bool
    message: Optional[str] = None


def feature_gate_check(
    subscription_holder: SubscriptionModelBase,
    limit_to_plans: Optional[List[str]] = None,
) -> bool:
    if not subscription_holder:
        raise NoSubscriptionFoundError(
            _("Couldn't find a model to check for a valid subscription.")
        )

    if not subscription_holder.has_active_subscription():
        raise NoSubscriptionFoundError(_("No active subscription was found."))

    if limit_to_plans:
        subscription = subscription_holder.active_stripe_subscription
        for item in subscription.items.select_related("price__product"):
            product_metadata = get_product_with_metadata(item.price.product).metadata
            if product_metadata.slug in limit_to_plans:
                return True
        raise PlanNotSupportedError(_("Your current plan does not support that."))
    else:
        # had an active subscription and wasn't limited to plans
        return True


def get_feature_gate_check(
    subscription_holder: SubscriptionModelBase,
    limit_to_plans: Optional[List[str]] = None,
) -> FeatureGateCheckResult:
    try:
        proceed = feature_gate_check(subscription_holder, limit_to_plans)
        return FeatureGateCheckResult(passed=proceed)
    except FeatureGateError as e:
        return FeatureGateCheckResult(passed=False, message=str(e))
