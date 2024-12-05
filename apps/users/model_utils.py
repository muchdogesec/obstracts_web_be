import requests
from allauth.socialaccount.models import SocialAccount
from .adapter import user_has_valid_totp_device
from .forms import CustomUserChangeForm, UploadAvatarForm
from .helpers import require_email_confirmation, user_has_confirmed_email_address
from .models import CustomUser
from .serializers import ChangeEmailSerializer, VerifyOtpSerializer, UserSerializer
from .utils import get_auth0_headers, get_auth0_management_token, update_auth0_user


def update_user_metadata(django_user_id):
    auth0_token = get_auth0_management_token()
    auth0_account = SocialAccount.objects.filter(user_id=django_user_id).first()
    if not auth0_account:
        return
    auth0_user_id = auth0_account.uid

    user = CustomUser.objects.get(id=django_user_id)
    team_ids = [str(team.id) for team in user.teams.all()]
    data = {"app_metadata": {"obstracts": { "user_id": str(django_user_id), "is_staff": user.is_staff, "team_ids": team_ids }}}
    update_auth0_user(
        auth0_user_id, data, auth0_token
    )

def make_user_staff_on_auth0(django_user_id):
    update_user_metadata(django_user_id)




def remove_user_from_staff_on_auth0(django_user_id):
    update_user_metadata(django_user_id)

def update_user_id_on_auth0(django_user_id):
    update_user_metadata(django_user_id)
