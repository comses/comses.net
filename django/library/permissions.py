from rest_framework.permissions import DjangoModelPermissions, BasePermission
from rest_framework.exceptions import PermissionDenied as DrfPermissionDenied
from wagtail.models import Site

from core.permissions import ObjectPermissions
from library.models import GitHubIntegrationConfiguration


class GitHubIntegrationPermission(BasePermission):
    """Permission class to check if user can use GitHub integration."""
    
    def has_permission(self, request, view):
        try:
            site = Site.objects.get(is_default_site=True)
            config = GitHubIntegrationConfiguration.for_site(site)
        except (Site.DoesNotExist, GitHubIntegrationConfiguration.DoesNotExist):
            raise DrfPermissionDenied("GitHub integration is not available")
        
        if not config.can_use_github_integration(request.user):
            raise DrfPermissionDenied("GitHub integration is not available")
        return True


class CodebaseReleaseUnpublishedFilePermissions(ObjectPermissions):
    perms_map = {
        "GET": [],
        "OPTIONS": [],
        "HEAD": [],
        "POST": [],
        "PUT": [],
        "PATCH": [],
        "DELETE": [],
    }

    object_perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.change_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }


class ModelDefinitionOnlyPermissions(DjangoModelPermissions):
    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }
