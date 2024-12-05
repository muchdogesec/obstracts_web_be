from django.apps import AppConfig


class SubscriptionConfig(AppConfig):
    name = "apps.subscriptions"
    label = "subscriptions"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import webhooks  # noqa F401
        from . import signals  # noqa F401
