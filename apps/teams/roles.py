from __future__ import annotations

from apps.users.models import CustomUser

ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"

ROLE_CHOICES = (
    # customize roles here
    (ROLE_OWNER, "Owner"),
    (ROLE_ADMIN, "Administrator"),
    (ROLE_MEMBER, "Member"),
)


def is_member(user: CustomUser, team) -> bool:
    if not team:
        return False
    return team.members.filter(id=user.id).exists()


def is_admin(user: CustomUser, team) -> bool:
    if not team:
        return False

    from .models import Membership

    return Membership.objects.filter(team=team, user=user).filter(role__in=[ROLE_ADMIN, ROLE_OWNER]).exists()


def is_owner(user: CustomUser, team) -> bool:
    if not team:
        return False

    from .models import Membership

    return Membership.objects.filter(team=team, user=user, role=ROLE_OWNER).exists()

def is_owner_by_user_id(user_id: str, team) -> bool:
    if not team:
        return False

    from .models import Membership

    return Membership.objects.filter(team=team, user_id=user_id, role=ROLE_OWNER).exists()