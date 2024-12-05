from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser
from .model_utils import make_user_staff_on_auth0, remove_user_from_staff_on_auth0


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = UserAdmin.list_display + ("date_joined",)
    list_filter = UserAdmin.list_filter + ("date_joined",)
    ordering = ("-date_joined",)

    fieldsets = UserAdmin.fieldsets + (("Custom Fields", {"fields": ("avatar",)}),)

    def save_model(self, request, obj, form, change):
        stored_user = CustomUser.objects.get(id=obj.id)
        update_on_auth0 = False
        if stored_user.is_staff != obj.is_staff:
            update_on_auth0 = True
        super().save_model(request, obj, form, change)
        if update_on_auth0:
            if obj.is_staff:
                make_user_staff_on_auth0((obj.id))
            else:
                remove_user_from_staff_on_auth0(obj.id)
