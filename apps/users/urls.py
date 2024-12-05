from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


app_name = "users"

router = DefaultRouter()
router.register(
    "user-management", views.UserManagementViewSet, basename="user-management"
)
router.register(
    "admin-user-management",
    views.UserAdminManagementViewSet,
    basename="admin-user-management",
)

urlpatterns = [
    path("", include(router.urls)),
]
