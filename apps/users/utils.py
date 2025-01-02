import requests
from django.conf import settings
from django.core.cache import cache
from allauth.socialaccount.models import SocialAccount




def get_auth0_headers(access_token):
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def _get_auth0_management_token():
    """Fetch Auth0 management token using client credentials"""
    data = {
        "grant_type": "client_credentials",
        "client_id": settings.AUTH0_CLIENT_ID,
        "client_secret": settings.AUTH0_CLIENT_SECRET,
        "audience": f"https://{settings.AUTH0_DOMAIN}/api/v2/",
    }

    response = requests.post(
        f"https://{settings.AUTH0_DOMAIN}/oauth/token",
        json=data,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_auth0_management_token():
    """Get Auth0 management token, either from cache or by fetching a new one."""
    token = cache.get('user__auth0_management_token')

    if not token:
        token = _get_auth0_management_token()
        cache.set('user__auth0_management_token', token, timeout=10800)

    return token


def update_auth0_user(user_id, payload, token):
    """Helper function to update user info on Auth0"""
    url = f"https://{settings.AUTH0_DOMAIN}/api/v2/users/{user_id}"
    headers = get_auth0_headers(token)
    response = requests.patch(url, json=payload, headers=headers)
    response.raise_for_status()
    return response


def update_auth0_user_by_django_user_id(django_user_id, payload):
    """Helper function to update user info on Auth0"""
    auth0_account = SocialAccount.objects.filter(user_id=django_user_id).first()
    if not auth0_account:
        return False
    user_id = auth0_account.uid

    # Get Auth0 management token
    auth0_token = get_auth0_management_token()
    update_auth0_user(user_id, payload, auth0_token)
    return True