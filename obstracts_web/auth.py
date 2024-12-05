from django.conf import settings
from allauth.socialaccount.providers.auth0.provider import Auth0Provider
from allauth.socialaccount.providers.auth0.views import Auth0OAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from django.views.decorators.csrf import csrf_exempt

from allauth.socialaccount.models import SocialApp
from apps.users.model_utils import update_user_id_on_auth0


class CustomAuth0OAuth2Adapter(Auth0OAuth2Adapter):
    provider_id = "auth0"

    provider_base_url = settings.AUTH0_URL

    access_token_url = "{0}/oauth/token".format(provider_base_url)
    authorize_url = "{0}/authorize".format(provider_base_url)
    profile_url = "{0}/userinfo".format(provider_base_url)

    def get_provider(self):
        return Auth0Provider(
            self.request,
            SocialApp(
                provider_id="auth0",
                name="main",
                client_id=settings.AUTH0_CLIENT_ID,
                secret=settings.AUTH0_CLIENT_SECRET,
                key="key",
                settings={},
            ),
        )

    def login(self, *args, **kwargs):
        pass


class Auth0Login(SocialLoginView):
    adapter_class = CustomAuth0OAuth2Adapter

    def process_login(self):
        CustomAuth0OAuth2Adapter(self.request).login(self.request, self.user)
        update_user_id_on_auth0(self.user.id)


    @csrf_exempt
    def post(self, *args, **kwargs):
        return super().post(*args, **kwargs)
