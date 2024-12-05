class SubscriptionConfigError(Exception):
    pass


class FeatureGateError(Exception):
    pass


class NoSubscriptionFoundError(FeatureGateError):
    pass


class PlanNotSupportedError(FeatureGateError):
    pass
