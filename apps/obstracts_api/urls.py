from django.urls import path, include
from rest_framework import routers
from drf_spectacular.views import SpectacularSwaggerView

from .schema import SchemaView
from .views import (
    AdminProxyView,
    ProxyView,
    FeedViewSet,
    FeedProxyView,
    TeamFeedProxyView,
    TeamFeedViewSet,
    OpenFeedProxyView,
    TeamTokenFeedViewSet,
    PostsByExtractionView,
    LatestPostView,
)


router = routers.DefaultRouter()
router.register("feeds", FeedViewSet, basename='feeds')


team_router = routers.DefaultRouter()
team_router.register("feeds", TeamFeedViewSet, basename='feeds')

api_router = routers.DefaultRouter()
api_router.register('', TeamTokenFeedViewSet, basename='team-token-feeds')

urlpatterns = router.urls + [
    path("team/<str:team_id>/", include(team_router.urls), name="team_feeds"),
    path("admin/api/v1/<path:path>", AdminProxyView.as_view(), name="admin-proxy"),
    path("proxy/open/feeds/<uuid:feed_id>/posts/", OpenFeedProxyView.as_view(), name=""),
    path("proxy/open/feeds/<uuid:feed_id>/posts/<uuid:post_id>/", OpenFeedProxyView.as_view(), name=""),
    path("proxy/open/feeds/<uuid:feed_id>/posts/<uuid:post_id>/markdown/", OpenFeedProxyView.as_view(), name=""),
    path("proxy/open/objects/scos/", OpenFeedProxyView.as_view(), name=""),
    path("proxy/open/object/<str:object_id>/reports/", OpenFeedProxyView.as_view(), name=""),
    path("proxy/teams/<str:team_id>/feeds/<str:feed_id>/<path:path>", TeamFeedProxyView.as_view(), name="proxy"),
    path("proxy/<path:path>", ProxyView.as_view(), name="proxy"),
    path("api/v1/feeds/<uuid:feed_id>/<path:path>", FeedProxyView.as_view(), name="proxy"),
    path("api/v1/feeds/", include(api_router.urls), name="team-feeds"),
    path('api/schema/schema-json', SchemaView.as_view(), name='schema-json'),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url="../schema-json"),
        name="swagger-ui",
    ),
    path(
        "objects/<str:object_id>/",
        PostsByExtractionView.as_view(),
    ),
    path(
        "teams/<uuid:team_id>/objects/<str:object_id>/",
        PostsByExtractionView.as_view(),
    ),
    path(
        "posts/",
        LatestPostView.as_view(),
    ),
    path(
        "teams/<uuid:team_id>/posts/",
        LatestPostView.as_view(),
    ),
]
