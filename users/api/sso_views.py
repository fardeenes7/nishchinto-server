from django.http import HttpResponse
from django.views import View
from rest_framework_simplejwt.tokens import RefreshToken

class SSOHubView(View):
    """
    Renders an invisible landing page for the SSO Handshake.
    If the user has a session in this domain, it transmits the JWT 
    to the parent window (the storefront/dashboard) via postMessage.
    """
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # Generate or fetch existing token
            refresh = RefreshToken.for_user(request.user)
            token = str(refresh.access_token)
            
            # Script to handshake with parent
            js_payload = f"""
                <script>
                    window.parent.postMessage({{
                        type: 'SSO_TOKEN_SYNC',
                        token: '{token}'
                    }}, '*');
                </script>
            """
        else:
            js_payload = "<!-- No active session found for SSO -->"
            
        return HttpResponse(f"<html><body>{js_payload}</body></html>")
