from django.contrib import admin

from .models import Player


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ["name", "sex", "date_of_birth", "team"]
    list_filter = ["team", "sex", "date_of_birth"]
