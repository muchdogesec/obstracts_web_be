"""Obstracts Web URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/stable/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from apps.teams.urls import team_urlpatterns as single_team_urls
from apps.subscriptions.urls import team_urlpatterns as subscriptions_team_urls
from apps.web.urls import team_urlpatterns as web_team_urls
from apps.web.sitemaps import StaticViewSitemap

from .auth import Auth0Login

sitemaps = {
    "static": StaticViewSitemap(),
}

# urls that are unique to using a team should go here
team_urlpatterns = [
    path("", include(web_team_urls)),
    path("subscription/", include(subscriptions_team_urls)),
    path("team/", include(single_team_urls)),
    path("example/", include("apps.teams_example.urls")),
]

urlpatterns = [
    path("", RedirectView.as_view(url="/admin")),
    path("admin/doc/", include("django.contrib.admindocs.urls")),
    # redirect Django admin login to main login page
    path("admin/login/", RedirectView.as_view(pattern_name="auth0_login")),
    path("admin/", admin.site.urls),
    path('obstracts_api/', include('apps.obstracts_api.urls')),
    path("team-management/<str:team_id>/", include(team_urlpatterns)),
    path("accounts/", include("allauth.urls")),
    path("users/", include("apps.users.urls")),
    path("subscriptions/", include("apps.subscriptions.urls")),
    path("teams/", include("apps.teams.urls")),
    # path("celery-progress/", include("celery_progress.urls")),
    # API docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Optional UI - you may wish to remove one of these depending on your preference
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # djstripe urls - for webhooks
    path("stripe/", include("djstripe.urls", namespace="djstripe")),
    # hijack urls for impersonation
    # path("hijack/", include("hijack.urls", namespace="hijack")),
    path("rest-auth/auth0/", Auth0Login.as_view(), name="auth0_api_login"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.ENABLE_DEBUG_TOOLBAR:
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
