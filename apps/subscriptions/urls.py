from django.urls import path
from rest_framework import routers


from . import views

app_name = "subscriptions"




router = routers.DefaultRouter()
router.register("api/plans", views.SubscriptionProductViewSet, basename="plans")

urlpatterns = router.urls

team_url_router = routers.DefaultRouter()
team_url_router.register(
    "subscription/init", views.TeamSubscriptionViewSet, basename="init-subscription"
)
team_urlpatterns = team_url_router.urls
