from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.utils.translation import gettext_lazy as _

from ..api_url_helpers import get_team_api_url_templates
from ..decorators import login_and_team_required, team_admin_required
from ..invitations import send_invitation
from ..models import Invitation
from ..serializers import TeamSerializer
from apps.users.serializers import CustomUserSerializer


@login_required
def manage_teams(request, path=""):
    return render(
        request,
        "teams/teams.html",
        {
            "api_urls": get_team_api_url_templates(),
            "user_json": CustomUserSerializer(request.user).data,
            "page_title": _("Manage Teams"),
        },
    )


@login_and_team_required
def manage_team(request, team_slug):
    team = request.team
    return render(
        request,
        "teams/manage_team_react.html",
        {
            "team": team,
            "team_json": TeamSerializer(team, context={"request": request}).data,
            "user_json": CustomUserSerializer(request.user).data,
            "active_tab": "manage-team",
            "api_urls": get_team_api_url_templates(),
        },
    )


@team_admin_required
@require_POST
def resend_invitation(request, team_slug, invitation_id):
    invitation = get_object_or_404(Invitation, team=request.team, id=invitation_id)
    send_invitation(invitation)
    return HttpResponse("Ok")
