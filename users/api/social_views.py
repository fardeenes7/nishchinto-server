from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView

class GoogleLogin(SocialLoginView):
    """
    Exposes a REST endpoint for Google OAuth2 login.
    Accepts an `access_token` or `code` and returns a JWT pair.
    """
    adapter_class = GoogleOAuth2Adapter
    callback_url = "http://localhost:8000/accounts/google/login/callback/" # Dev default
    client_class = OAuth2Client
