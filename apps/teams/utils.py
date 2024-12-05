from apps.users.utils import update_auth0_user_by_django_user_id
from apps.users.model_utils import update_user_metadata
from .models import Membership


def update_user_teams_on_auth0(user_id):
    update_user_metadata(user_id)
