from django.http import Http404


def team(request):
    return {
        "team": getattr(request, "team", None),
    }


def user_teams(request):
    if not request.user.is_authenticated:
        return {}

    try:
        current_team = getattr(request, "team", None)
        if not current_team:
            return {}
    except Http404:
        # if the above raises a 404 it can cause a 500 error instead of letting it propagate
        return {}

    other_membership = request.user.membership_set
    if current_team and current_team.pk:
        other_membership = other_membership.exclude(team=current_team)
    return {
        "other_teams": {
            membership.team.name: membership.team.dashboard_url
            for membership in other_membership.select_related("team")
        }
    }
