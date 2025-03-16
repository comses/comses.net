from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from django.conf import settings
from rest_framework.permissions import BasePermission


class APIKeyAuthentication(BaseAuthentication):
    def authenticate_header(self, request):
        return "X-API-Key"

    def authenticate(self, request):
        api_key = request.META.get("HTTP_X_API_KEY")

        if not api_key:
            raise AuthenticationFailed("No API key")

        if api_key != settings.LLM_SPAM_CHECK_API_KEY:
            raise AuthenticationFailed("Invalid API key")

        return (None, None)
