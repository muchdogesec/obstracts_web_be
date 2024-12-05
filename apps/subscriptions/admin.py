from django.contrib import admin
from .models import SubscriptionConfig


@admin.register(SubscriptionConfig)
class SubscriptionConfigAdmin(admin.ModelAdmin):
    list_display = ["key", "value"]
    list_filter = ["key"]
