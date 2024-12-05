from rest_framework import serializers

from .models import CustomUser


class CustomUserSerializer(serializers.ModelSerializer):
    """
    Basic serializer to pass CustomUser details to the front end.
    Extend with any fields your app needs.
    """

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "avatar_url",
            "get_display_name",
        )


class ChangeEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyOtpSerializer(serializers.Serializer):
    otp = serializers.CharField(write_only=True)
    otp_key = serializers.CharField(write_only=True)


class UserSerializer(serializers.ModelSerializer):
    teams = serializers.SerializerMethodField()
    class Meta:
        model = CustomUser
        exclude = ("password", "is_superuser")

    def get_teams(self, obj):
        return [{"name": str(membership.team.name), "id": str(membership.team.id), "owner_id": membership.team.owner_id} for membership in obj.membership_set.all()]
