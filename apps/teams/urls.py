from django.urls import path, include
from rest_framework import routers
from . import views


app_name = "teams"

# DRF config for API views (required for React Teams, implementation, optional otherwise)
router = routers.DefaultRouter()
router.register("api/teams", views.TeamViewSet)
router.register("api/admin", views.AdminTeamViewSet, basename='admin-team')
router.register("api/user/invitations", views.UserInvitationViewSet)
router.register("api/user/api-keys", views.UserApiKeyViewSet)
router.register(
    "api/user/complete-registration",
    views.UserCompleteRegistrationViewSet,
    basename="complete-registration",
)

urlpatterns = router.urls


single_team_router = routers.DefaultRouter()
single_team_router.register("invitations", views.TeamInvitationViewSet)
single_team_router.register("api-keys", views.TeamApiKeyViewSet)


urlpatterns += [
    path(
        "api/teams/<uuid:team_id>/",
        include(single_team_router.urls),
    ),
]
team_urlpatterns = []