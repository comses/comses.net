"""Enforce the external authentication policy independently of provider credentials."""

from django.conf import settings
from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin


def external_auth_enabled():
    return settings.EXTERNAL_AUTH_ENABLED is True


class ExternalAuthMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if external_auth_enabled():
            return None
        # Restored SocialApp rows can supply credentials independently of settings.
        # Block callbacks as well as initiation, before an adapter can contact an IdP.
        if view_func.__module__.startswith("allauth.socialaccount.") or request.resolver_match.view_name in {
            "core:discourse-sso",
            "core:librarian-sso",
        }:
            return HttpResponseForbidden("External authentication is disabled on this deployment.")
        return None
