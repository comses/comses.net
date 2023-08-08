import logging

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from .permissions import ViewRestrictedObjectPermissions

logger = logging.getLogger(__name__)


def _common_namespace_path(model):
    meta = model._meta
    app_label = meta.app_label
    return "{0}/{1}".format(app_label, meta.verbose_name_plural.replace(" ", "_"))


class CommonViewSetMixin:
    """
    Provide conventions for list, retrieve, and delete URL routes + template paths for
    ViewSets.

    List => <namespace>/list.<ext>
    Retrieve => <namespace>/retrieve.<ext>
    Delete => <namespace>/delete.<ext>

    Override 'namespace' property to set the namespace directly,

    namespace = 'library/codebases'

    By default the namespace will be set to <app-label>/<model-name> which is typically not pluralized. This namespace
    is used for the URL namespace as well as the template filesystem namespace, where the template files are discovered.

    Override 'ext' property to set the file extension, default is 'jinja'


    """

    ALLOWED_ACTIONS = ("list", "retrieve", "delete")
    namespace = None
    ext = "jinja"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.templates = {}

    def _get_namespace(self):
        if self.namespace is None:
            # FIXME: assumes everything mixing this in will have a queryset property
            self.namespace = _common_namespace_path(self.queryset.model)
        return self.namespace

    def get_template_names(self):
        namespace = self._get_namespace()
        file_ext = self.ext
        ts = self.templates
        if not ts:
            for action in self.ALLOWED_ACTIONS:
                # by convention, templates should be named <action>.<file-ext> and discovered in TEMPLATE_DIRS under
                # `django/<app-name>/jinja2/<namespace>/<action>.<file_ext>`.
                ts[action] = ["{0}/{1}.{2}".format(namespace, action, file_ext)]
        if self.action in ts:
            return ts[self.action]
        # FIXME: this appears to be caused by https://github.com/encode/django-rest-framework/issues/6196
        error_message = f"Unhandled action {self.action} in namespace {namespace} - expecting list / retrieve / delete."
        logger.warning(error_message)
        raise NotFound(error_message)


class PermissionRequiredByHttpMethodMixin:
    """
    Classes using this mixin must override model and optionally namespace.
    """

    namespace = None
    model = None

    def get_template_names(self):
        # NB: assumes everything mixing this in will have a model attribute and that edit pages are always
        # edit.jinja
        if self.namespace is None:
            namespace = _common_namespace_path(self.model)
        else:
            namespace = self.namespace
        return ["{0}/{1}".format(namespace, "edit.jinja")]

    def get_required_permissions(self, request=None):
        perms = ViewRestrictedObjectPermissions.get_required_object_permissions(
            self.method, self.model
        )
        return perms

    def check_permissions(self):
        user = self.request.user
        # Because user.has_perms hasn't been called yet django-guardian
        # hasn't replaced the AnonymousUser with an actual user object
        if user.is_anonymous:
            return redirect_to_login(
                self.request.get_full_path(), settings.LOGIN_URL, "next"
            )
        if hasattr(self, "get_object"):
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
        return super().dispatch(request, *args, **kwargs)


class HtmlRetrieveModelMixin:
    """
    Retrieve a model instance. If renderer if html pass the instance to the template directly
    """

    context_object_name = "object"

    def get_retrieve_context(self, instance):
        context = {self.context_object_name: instance}
        return context

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.accepted_renderer.format == "html":
            return Response(self.get_retrieve_context(instance))

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class HtmlListModelMixin:
    """
    List a queryset. If renderer if html pass the queryset to the template directly
    """

    context_list_name = "object"

    def get_list_context(self, page_or_queryset):
        context = {self.context_list_name: page_or_queryset}
        if self.paginator:
            context["paginator_data"] = self.paginator.get_context_data(context)
        return context

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if request.accepted_renderer.format == "html":
            context = self.get_list_context(page or queryset)
            return Response(context)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
