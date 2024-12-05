from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from django.utils.translation import gettext_lazy as _
from allauth.socialaccount.models import SocialAccount
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError as DRFValidationError,
    NotFound,
)
from rest_framework import filters

from apps.api.models import TeamApiKey
from apps.api.permissions import IsAuthenticatedOrHasUserAPIKey
from apps.subscriptions.helpers import subscribe_team_to_initial_subscription


from apps.users.views import (
    get_auth0_headers,
    get_auth0_management_token,
    update_auth0_user,
)
from ..invitations import send_invitation, process_invitation
from ..models import Team, Invitation, Membership, TeamProfile
from ..permissions import TeamAccessPermissions, TeamModelAccessPermissions
from ..roles import ROLE_ADMIN, ROLE_OWNER, is_admin, is_member, is_owner, is_owner_by_user_id
from ..serializers import (
    MembershipSerializer,
    InvitationSerializer,
    InvitationWithTeamSerializer,
    TeamSerializer,
    TeamWithAllowedApiAccessSerializer,
    TeamWithLimitsSerializer,
    UserCompleteRegistrationSerializer,
    MembershipWithTeamSerializer,
    AddProfileSerializer,
    RemoveProfileSerializer,
    ChangeUserTeamRoleSerializer,
    RemoveUserSerializer,
    AdminTeamSerializer,
    TeamApiKeySerializer,
    ApiKeySerializer,
)
from ...utils.obstracts import get_profile as get_obstract_profile
from ..utils import update_user_teams_on_auth0


@extend_schema_view(
    create=extend_schema(operation_id="teams_create"),
    list=extend_schema(operation_id="teams_list"),
    retrieve=extend_schema(operation_id="teams_retrieve"),
    update=extend_schema(operation_id="teams_update"),
    partial_update=extend_schema(operation_id="teams_partial_update"),
    destroy=extend_schema(operation_id="teams_destroy"),
)
class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamWithAllowedApiAccessSerializer
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ['name', 'description']
    permission_classes = (IsAuthenticatedOrHasUserAPIKey, TeamAccessPermissions | IsAdminUser)

    def get_queryset_data(self):
        if self.action == 'list':
            return self.request.user.teams.order_by("name")
        # filter queryset based on logged in user
        if self.request.user.is_staff:
            return Team.objects.all()
        return self.request.user.teams.order_by("name")

    def get_queryset(self):
        return self.get_queryset_data().select_related('subscription')

    def check_object_permissions(self, request, obj):
        if self.action not in ['list', 'subscribe', 'unsubscribe']:
            if obj.is_private:
                return self.permission_denied(request, "User has no permission to this team")
        if self.action == 'destroy':
            if not is_owner(self.request.user, obj):
                return self.permission_denied(request, "User has no permission to delete this team")
        return True

    def perform_create(self, serializer):
        # ensure logged in user is set on the model during creation
        team = serializer.save()
        team.members.add(self.request.user, through_defaults={"role": "owner"})
        update_user_teams_on_auth0(self.request.user.id)
        subscribe_team_to_initial_subscription(team)

    @action(detail=True, methods=["GET"], url_path="limits")
    def limit_details(self, *args, **kwargs):
        team = self.get_object()
        team_obj = Team.objects.filter(id=team.id).annotate(
            members_count=Count('members', distinct=True),
            invitations_count=Count('invitations', filter=Q(
                Q(invitations__is_accepted=False) &
                Q(invitations__is_cancelled=False),
            ), distinct=True),
            feed_count=Count('feeds', distinct=True)
        ).select_related('subscription').first()
        serializer = TeamWithLimitsSerializer(team_obj)
        serializer.context['view'] = self
        serializer.context['request'] = self.request
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="membership")
    def memberships(self, *args, **kwargs):
        members = Membership.objects.filter(user=self.request.user).select_related(
            "team"
        )
        serializer = MembershipWithTeamSerializer(members, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["POST"], url_path="change-role")
    def change_role(self, *args, **kwargs):
        obj = self.get_object()
        serializer = ChangeUserTeamRoleSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data["user_id"]
        role  = serializer.validated_data["role"]
        if is_owner_by_user_id(user_id, obj):
            if Membership.objects.filter(team=obj, role=ROLE_OWNER).count() < 2:
                raise DRFValidationError("Team must have at least one owner")
        Membership.objects.filter(team=obj, user=user_id).update(role=role)
        update_user_teams_on_auth0(user_id)
        return Response({"status": "success"})

    @action(detail=True, methods=["POST"], url_path="remove-member")
    def remove_member(self, *args, **kwargs):
        obj = self.get_object()
        serializer = RemoveUserSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data["user_id"]
        if is_owner_by_user_id(user_id, obj):
            if Membership.objects.filter(team=obj, role=ROLE_OWNER).count() < 2:
                raise DRFValidationError("User is the only owner for this team, and can't be removed")
        Membership.objects.filter(team=obj, user=user_id).delete()
        update_user_teams_on_auth0(user_id)
        return Response({"status": "success"})

    @action(detail=True, methods=["POST"], url_path="leave-team")
    def leave_team(self, *args, **kwargs):
        obj = self.get_object()
        membership = Membership.objects.filter(team=obj, user=self.request.user)
        if is_owner(self.request.user, obj):
            if Membership.objects.filter(team=obj, role=ROLE_ADMIN).count() < 2:
                raise DRFValidationError("You are the only owner for this team, and can't leave")
        Membership.objects.filter(team=obj, user=self.request.user).delete()
        update_user_teams_on_auth0(self.request.user.id)
        return Response({"status": "success"})

    @action(detail=True, methods=["get"], url_path="members")
    def members(self, *args, **kwargs):
        obj = self.get_object()
        serializer = MembershipSerializer(obj.sorted_memberships, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="profiles")
    def get_profiles(self, *args, **kwargs):
        obj = self.get_object()
        profiles = TeamProfile.objects.filter(team_id=obj.id)
        return Response([profile.metadata for profile in profiles])

    @action(detail=True, methods=["post"], url_path="add-profile")
    def add_profile(self, *args, **kwargs):
        obj = self.get_object()
        serializer = AddProfileSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        profile_id = serializer.validated_data["profile_id"]
        profile_data = get_obstract_profile(profile_id)
        if not profile_data.get("id"):
            raise NotFound()
        TeamProfile.objects.create(
            team_id=obj.id, profile_id=profile_id, metadata=profile_data
        )
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="remove-profile")
    def remove_profile(self, *args, **kwargs):
        obj = self.get_object()
        serializer = RemoveProfileSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        profile_id = serializer.validated_data["profile_id"]
        TeamProfile.objects.filter(team_id=obj.id, profile_id=profile_id).delete()
        return Response(serializer.data)

    def perform_destroy(self, instance):
        if not is_owner(self.request.user, instance):
            raise PermissionDenied('Only owners can delete a team')
        instance.close_customer_and_subscriptions()
        instance.delete()


@extend_schema(tags=["teams"])
@extend_schema_view(
    create=extend_schema(operation_id="invitations_create"),
    list=extend_schema(operation_id="invitations_list"),
    retrieve=extend_schema(operation_id="invitations_retrieve"),
    update=extend_schema(operation_id="invitations_update"),
    partial_update=extend_schema(operation_id="invitations_partial_update"),
    destroy=extend_schema(operation_id="invitations_destroy"),
)
class TeamInvitationViewSet(viewsets.ModelViewSet):
    queryset = Invitation.objects.all()
    serializer_class = InvitationSerializer
    permission_classes = (IsAuthenticatedOrHasUserAPIKey, TeamModelAccessPermissions)

    @property
    def team(self):
        team = get_object_or_404(Team, id=self.kwargs["team_id"])
        if team.is_private:
            raise NotFound()
        if self.request.user.is_staff or is_member(self.request.user, team):
            return team
        else:
            raise PermissionDenied()

    def _ensure_team_match(self, team):
        if team != self.team:
            raise DRFValidationError("Team set in invitation must match URL")

    def _ensure_no_pending_invite(self, team, email):
        if Invitation.objects.filter(team=team, email=email, is_accepted=False):
            raise DRFValidationError(
                {
                    # this mimics the same validation format used by the serializer so it can work easily on the front end.
                    "email": [
                        _(
                            'There is already a pending invitation for {}.'
                        ).format(email)
                    ]
                }
            )

    def get_queryset(self):
        # filter queryset based on logged in user and team
        query = self.queryset.filter(team=self.team)
        is_accepted = self.request.query_params.get("is_accepted")
        if is_accepted:
            query = query.filter(is_accepted=is_accepted == "true")
        return query

    def perform_create(self, serializer):
        # ensure logged in user is set on the model during creation
        # and can access the underlying team
        team = self.team
        self._ensure_team_match(team)
        self._ensure_no_pending_invite(team, serializer.validated_data["email"])

        # unfortunately, the permissions class doesn't handle creation well
        # https://www.django-rest-framework.org/api-guide/permissions/#limitations-of-object-level-permissions
        if not self.request.user.is_staff and not is_admin(self.request.user, team):
            raise PermissionDenied()
        team_user_count = Membership.objects.filter(team=team).count()
        team_invite_count = Invitation.objects.filter(team=team).count()
        allowed_user_count = team.get_user_limit()
        if allowed_user_count and allowed_user_count < (team_user_count + team_invite_count):
            raise DRFValidationError({
                "code": "E01",
                "message": "Team subscription user count exceeded",
            })
        invitation = serializer.save(invited_by=self.request.user, team_id=team.id)
        send_invitation(invitation)

    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.context['is_owner'] = is_owner(self.request.user, self.team)
        serializer.is_valid(raise_exception=True)
        team = self.team
        self._ensure_team_match(team)
        if not self.request.user.is_staff and not is_admin(self.request.user, team):
            raise PermissionDenied()
        team_user_count = Membership.objects.filter(team=team).count()
        team_invite_count = Invitation.objects.filter(team=team, is_cancelled=False, is_accepted=False).count()
        allowed_user_count = team.get_user_limit()
        available_user_slot = allowed_user_count - (team_user_count + team_invite_count)
        if allowed_user_count and available_user_slot < len(serializer.validated_data):
            raise DRFValidationError({
                "code": "E01",
                "message": "Team subscription user count exceeded",
            })

        for item in serializer.validated_data:
            self._ensure_no_pending_invite(team, item["email"])

        invitations = Invitation.objects.bulk_create(
            Invitation(**item,invited_by=self.request.user, team_id=team.id) for item in serializer.validated_data
        )
        for invitation in invitations:
            send_invitation(invitation)
        return Response({})

        @action(detail=True, methods=["post"], url_path="cancel-invitation")
        def get_my_pending_invitations(self, *args, **kwargs):
            invitation = self.get_object()
            invitation.is_cancelled = True
            invitation.save()
            return Response(serializer.data)


class UserInvitationViewSet(
    viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin
):
    queryset = Invitation.objects.all()
    serializer_class = InvitationWithTeamSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Invitation.objects.filter(
            email=self.request.user.email, is_accepted=False, is_cancelled=False
        )

    @action(detail=True, methods=["post"], url_path="cancel-invitation")
    def cancel_invitation(self, *args, **kwargs):
        invitation = self.get_object()
        invitation.delete()
        return Response({})

    @action(detail=True, methods=["post"], url_path="accept-invitation")
    def accept_invitation(self, *args, **kwargs):
        invitation = self.get_object()
        if self.request.user.is_authenticated and is_member(
            self.request.user, invitation.team
        ):
            raise DRFValidationError("User is already a member of this team")
        process_invitation(invitation, self.request.user)
        update_user_teams_on_auth0(self.request.user.id)
        return Response({})


class UserCompleteRegistrationViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    serializer_class = UserCompleteRegistrationSerializer
    permission_classes = (IsAuthenticated,)
    allowed_methods = ["POST"]

    def perform_create(self, serializer):
        serializer.save()
        auth0_token = get_auth0_management_token()
        auth0_account = SocialAccount.objects.get(user_id=self.request.user.id)
        user_id = auth0_account.uid
        update_auth0_user(user_id, {"app_metadata": {"registered": True}}, auth0_token)

class MyAdminPermission(IsAdminUser):
    def has_permission(self, request, view):
        print(request.user, request.user.is_staff, '\n'*20)
        return bool(request.user and request.user.is_staff)

class AdminTeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = AdminTeamSerializer
    permission_classes = (IsAuthenticated, IsAdminUser,)
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ['name', 'description']

    def get_queryset(self):
        return Team.objects.annotate(
            members_count=Count('members', distinct=True),
            invitations_count=Count('invitations', filter=Q(
                Q(invitations__is_accepted=False) &
                Q(invitations__is_cancelled=False),
            ), distinct=True),
            feed_count=Count('feeds', distinct=True)
        ).select_related('subscription')

class TeamApiKeyViewSet(viewsets.ModelViewSet):
    queryset = TeamApiKey.objects.all()
    serializer_class = TeamApiKeySerializer
    permission_classes = (IsAuthenticated, TeamModelAccessPermissions)

    @property
    def team(self):
        team = get_object_or_404(Team, id=self.kwargs["team_id"])
        if not team.get_allowed_api_access():
            raise DRFValidationError("Upgrade your subscription to be able to access the API")
        if self.request.user.is_staff or is_member(self.request.user, team):
            return team
        else:
            raise PermissionDenied()


class UserApiKeyViewSet(viewsets.ModelViewSet):
    queryset = TeamApiKey.objects.all()
    serializer_class = ApiKeySerializer
    permission_classes = (IsAuthenticatedOrHasUserAPIKey,)
    lookup_field = 'key_id'

    def get_queryset(self):
        return TeamApiKey.objects.filter(user=self.request.user)
