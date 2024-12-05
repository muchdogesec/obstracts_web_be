from typing import List

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .exceptions import SubscriptionConfigError
from .feature_gating import get_feature_gate_check


class redirect_subscription_errors(object):
    """
    Meant to be used with django views only.
    """

    def __init__(self, f):
        self.f = f

    def __call__(self, request, *args, **kwargs):
        try:
            return self.f(request, *args, **kwargs)
        except SubscriptionConfigError as e:
            return TemplateResponse(
                request, "subscriptions/bad_config.html", {"error": str(e)}, status=500
            )


class _ActiveSubscriptionRequired:
    # decorator follows this pattern: https://stackoverflow.com/a/7492124/8207

    def __init__(self, f, limit_to_plans=None):
        self.f = f
        self.limit_to_plans = limit_to_plans or []

    def __call__(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseRedirect(
                "{}?next={}".format(reverse("account_login"), request.path)
            )

        subscription_holder = request.team
        check_result = get_feature_gate_check(subscription_holder, self.limit_to_plans)
        if not check_result.passed:
            messages.info(
                request,
                _("Sorry, but you don't have access to that. {details}").format(
                    details=check_result.message
                ),
            )
            return HttpResponseRedirect(
                reverse(
                    "subscriptions_team:subscription_details", args=[request.team.slug]
                )
            )
        else:
            return self.f(request, *args, **kwargs)


def active_subscription_required(function=None, limit_to_plans: List[str] = None):
    """
    Prevents accessing a view unless the user has an active subscription.
    You can optionally limit to a list of plans (by slug) which should allow access
    (default is any active subscription).
    """
    if function:
        return _ActiveSubscriptionRequired(function, limit_to_plans)
    else:

        def wrapper(function):
            return _ActiveSubscriptionRequired(function, limit_to_plans)

        return wrapper
