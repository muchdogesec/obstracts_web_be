import uuid

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from apps.api.models import TeamApiKey
from rest_framework.validators import UniqueValidator

from apps.subscriptions.serializers import SubscriptionSerializer
from .invitations import send_invitation, process_invitation
from .roles import is_admin, is_member
from .helpers import get_next_unique_team_slug
from .models import Team, Membership, Invitation
from .roles import is_admin, is_owner


class MembershipSerializer(serializers.ModelSerializer):
    user_id = serializers.ReadOnlyField(source="user.id")
    email = serializers.ReadOnlyField(source="user.email")
    first_name = serializers.ReadOnlyField(source="user.first_name")
    last_name = serializers.ReadOnlyField(source="user.last_name")
    display_name = serializers.ReadOnlyField(source="user.get_display_name")

    class Meta:
        model = Membership
        fields = ("id", "user_id", "first_name", "last_name", "display_name", "role", "email")


class InvitationSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    invited_by = serializers.ReadOnlyField(source="invited_by.get_display_name")
    is_accepted = serializers.ReadOnlyField()

    def validate_role(self, value):
        if value == 'owner' and not self.context['is_owner']:
            raise ValidationError('Only a owner can invite another user as a owner')
        return value

    class Meta:
        model = Invitation
        fields = ("id", "team_id", "email", "role", "invited_by", "is_accepted")


class BaseTeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = (
            "id",
            "name",
            "description",
            "is_private",
            "owner_id",
            "has_active_subscription",
        )

class TeamSerializer(serializers.ModelSerializer):
    is_admin = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = (
            "id",
            "name",
            "description",
            "is_admin",
            "is_owner",
            "is_private",
            "owner_id",
            "has_active_subscription",
        )

    def get_is_admin(self, obj) -> bool:
        return is_admin(self.context["request"].user, obj)

    def get_is_owner(self, obj) -> bool:
        return is_owner(self.context["request"].user, obj)

    def create(self, validated_data):
        team_name = validated_data.get("name", None)
        validated_data["slug"] = validated_data.get(
            "slug", get_next_unique_team_slug(team_name)
        )
        user_id = self.context["request"].user.id
        validated_data['owner_id'] = user_id
        result = super().create(validated_data)
        return result

class TeamWithAllowedApiAccessSerializer(TeamSerializer):
    subscription = SubscriptionSerializer(read_only=True)
    class Meta:
        model = Team
        fields = TeamSerializer.Meta.fields + (
            'allowed_api_access',
            'allowed_data_download',
            'subscription',
        )


class MembershipWithTeamSerializer(MembershipSerializer):
    team = TeamSerializer()

    class Meta:
        model = Membership
        fields = (
            "id",
            "user_id",
            "first_name",
            "last_name",
            "display_name",
            "role",
            "team",
        )


class InvitationWithTeamSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    invited_by = serializers.ReadOnlyField(source="invited_by.get_display_name")
    is_accepted = serializers.ReadOnlyField()
    team = TeamSerializer()

    class Meta:
        model = Invitation
        fields = ("id", "team_id", "team", "email", "role", "invited_by", "is_accepted")


class UserCompleteRegistrationSerializer(serializers.Serializer):
    team = TeamSerializer(
        write_only=True,
        required=False,
    )
    accepted_invitations = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
    )
    rejected_invitations = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
    )

    def save(self, **kwargs):
        view = self.context.get("view")
        user = view.request.user
        # Extract the data
        team_data = self.validated_data.get("team")
        accepted_invitations = self.validated_data.get("accepted_invitations", [])
        rejected_invitations = self.validated_data.get("rejected_invitations", [])

        # Process accepted invitations
        invitations = Invitation.objects.filter(email=user.email).filter(
            id__in=accepted_invitations
        )
        for invitation in invitations:
            if is_member(user, invitation.team):
                continue
            process_invitation(invitation, user)

        # Cancel rejected invitations
        Invitation.objects.filter(email=user.email).filter(
            id__in=rejected_invitations
        ).update(is_cancelled=True)

        # Save the team
        team_serializer = TeamSerializer(data=team_data)
        if team_serializer.is_valid(raise_exception=False):
            team = team_serializer.save()
            team.members.add(user, through_defaults={"role": "admin"})
            return team
        return {}

class AddProfileSerializer(serializers.Serializer):
    profile_id = serializers.UUIDField()

class RemoveProfileSerializer(serializers.Serializer):
    profile_id = serializers.UUIDField()

class RemoveUserSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()

class ChangeUserTeamRoleSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    role = serializers.CharField()

class TeamWithLimitsSerializer(TeamSerializer):
    members_count = serializers.IntegerField()
    invitations_count = serializers.IntegerField()
    feed_count = serializers.IntegerField()
    limits_exceeded = serializers.SerializerMethodField()
    api_keys_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = TeamSerializer.Meta.fields + (
            'allowed_data_download',
            'allowed_api_access',
            'members_count',
            'invitations_count',
            'feed_count',
            'feed_limit',
            'user_limit',
            'limits_exceeded',
            'api_keys_count',
        )

    def get_api_keys_count(self, obj):
        return TeamApiKey.objects.filter(team=obj).count()

    def get_limits_exceeded(self, obj):
        return obj.user_limit < obj.members_count + obj.invitations_count or obj.feed_limit < obj.feed_count


class AdminTeamSerializer(TeamWithLimitsSerializer):
    user_emails = serializers.SerializerMethodField()
    subscription = SubscriptionSerializer(read_only=True)

    class Meta:
        model = Team
        fields = TeamWithLimitsSerializer.Meta.fields + (
            'user_emails',
            "subscription",
        )

    def get_user_emails(self, obj):
        return [member.email for member in obj.members.all()]

class TeamApiKeySerializer(serializers.Serializer):
    api_key = serializers.CharField(read_only=True)
    key = serializers.CharField(read_only=True)
    name = serializers.CharField(write_only=True)

    def create(self, validated_data):
        user = self.context['request'].user
        team = self.context['view'].team
        name = validated_data['name']
        membership = Membership.objects.get(team=team, user=user)
        api_key, key = TeamApiKey.objects.create_key(
            key_id=str(uuid.uuid4()), name=name, user=user, membership=membership, team=team
        )
        key = api_key.clear_key = key
        api_key.save()
        return {
            "api_key": api_key,
            "key": key,
        }

class ApiKeySerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name')

    class Meta:
        model = TeamApiKey
        fields = ('id', 'name', 'team_name', 'key_id', 'last_used', 'status')
