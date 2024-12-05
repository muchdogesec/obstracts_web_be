import uuid
from django.db import migrations


def create_subscription_trial_duration(apps, schema_editor):
    SubscriptionConfig = apps.get_model("subscriptions", "SubscriptionConfig")
    SubscriptionConfig.objects.create(key="subscription_trial_duration_days", value=0)
    SubscriptionConfig.objects.create(key="subscription_trial_duration_hours", value=0)
    SubscriptionConfig.objects.create(
        key="subscription_trial_duration_minutes", value=10
    )


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_subscription_trial_duration, reverse_func),
    ]
