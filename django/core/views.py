import os

from django.views.generic import DetailView, TemplateView
from django.contrib.auth.views import redirect_to_login
from django.http import Http404
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework.exceptions import PermissionDenied as DrfPermissionDenied

from .permissions import ComsesPermissions
from . import summarization

import logging

logger = logging.getLogger(__name__)


@api_view(['POST'], exclude_from_schema=True)
@permission_classes([])
def summarize_text(request):
    return Response(summarization.summarize_to_text(request.data['description'], 2))


class FormViewSetMixin:
    """
    Provide routing and template discovery conventions for ViewSets that need to render forms. These could also just be
    explicit in urls.py but this helps to keep them in one place.


    Override 'namespace' property to set the namespace directly, e.g.,

    namespace = 'library/codebases'

    By default the namespace will be set to <app-label>/<model-name> which is typically not pluralized. This namespace
    is used for the URL namespace as well as the template filesystem namespace, where the template files are discovered.
    """

    ACTIONS = ('list', 'retrieve', 'delete')

    def _get_namespace(self):
        namespace = getattr(self, 'namespace', None)
        if namespace is None:
            meta = self.get_queryset().model._meta
            app_label = meta.app_label
            namespace = '{0}/{1}'.format(app_label, meta.verbose_name_plural.replace(' ', '_'))
            self.namespace = namespace
        return namespace

    def get_template_names(self):
        # default to the lowercased model name
        namespace = self._get_namespace()
        file_ext = getattr(self, 'ext', 'jinja')
        templates = {}
        for action in self.ACTIONS:
            # by convention, templates will be named <action>.<file-ext> and discovered in the template filesystem under
            # `django/<app-name>/templates/<namespace>/<action>.<file-ext>`
            template_name = '{0}.{1}'.format(action, file_ext)
            templates[action] = ['{0}/{1}'.format(namespace, template_name), template_name]
        if self.action in templates.keys():
            return templates[self.action]
        # FIXME: is this an appropriate default or should we return a 404?
        return ['rest_framework/api.html']


class PermissionRequiredByHttpMethodMixin:
    namespace = None

    def get_template_names(self):
        if self.namespace is None:
            namespace = self.model._meta.verbose_name_plural.replace(' ', '_')
        else:
            namespace = self.namespace

        return [os.path.join(self.model._meta.app_label, namespace, 'edit.jinja')]

    def get_required_permissions(self, request=None):
        model = self.model
        template_perms = ComsesPermissions.perms_map[self.method]
        perms = [template_perm % {'app_label': model._meta.app_label,
                                  'model_name': model._meta.model_name}
                 for template_perm in template_perms]
        return perms

    def check_permissions(self):
        user = self.request.user
        # Because user.has_perms hasn't been called yet django-guardian
        # hasn't replaced the AnonymousUser with an actual user object
        if user.is_anonymous():
            return redirect_to_login(self.request.get_full_path(),
                                     settings.LOGIN_URL,
                                     'next')
        if hasattr(self, 'get_object'):
            obj = self.get_object()
        else:
            obj = None
        perms = self.get_required_permissions()
        if user.has_perms(perms, obj):
            return None
        else:
            raise PermissionDenied

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        self.args = args
        self.kwargs = kwargs
        response = self.check_permissions()
        if response:
            return response
        return super().dispatch(request, *args,
                                **kwargs)


class FormUpdateView(PermissionRequiredByHttpMethodMixin, DetailView):
    method = 'PUT'


class FormCreateView(PermissionRequiredByHttpMethodMixin, TemplateView):
    method = 'POST'


def log_request_failure(exc, request):
    logger.info(
        'Request on url {url} by user "{username}" with content_type {content_type} failed with exception {exception}'
        .format(url=request.path, username=request.user.username, content_type=request.accepted_media_type,
                exception=str(exc)))


def rest_exception_handler(exc, context):
    request = context.get('request')
    if request and request.accepted_media_type == 'text/html':
        if isinstance(exc, Http404):
            return page_not_found(request, context=context)
        elif isinstance(exc, (PermissionDenied, DrfPermissionDenied)):
            return permission_denied(request, context=context)
        else:
            return server_error(request, context=context)
    else:
        log_request_failure(exc, request)
        return exception_handler(exc, context)


def permission_denied(request, context=None):
    response = render(
        request=request,
        template_name='403.jinja',
        context=context,
        status=403)
    return response


def page_not_found(request, context=None):
    response = render(
        request=request,
        template_name='404.jinja',
        context=context,
        status=404)
    return response


def server_error(request, context=None):
    response = render(
        request=request,
        template_name='500.jinja',
        context=context,
        status=500)
    return response
