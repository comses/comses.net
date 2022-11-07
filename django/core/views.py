import base64
import hashlib
import hmac
import logging
from collections import OrderedDict
from urllib import parse

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import (
    Http404,
    HttpResponseBadRequest,
    HttpResponseRedirect,
    HttpResponseServerError,
)
from django.shortcuts import render
from django.views.generic import DetailView, TemplateView
from rest_framework import viewsets, mixins
from rest_framework.exceptions import (
    PermissionDenied as DrfPermissionDenied,
    NotAuthenticated,
    NotFound,
    APIException,
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .discourse import build_discourse_url
from .permissions import ViewRestrictedObjectPermissions

logger = logging.getLogger(__name__)


def make_error(request, should_raise=True):
    if should_raise:
        raise ValueError("This is an unhandled error")
    return HttpResponseServerError("This is an unhandled server error response.")


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
        model = self.model
        template_perms = ViewRestrictedObjectPermissions.perms_map[self.method]
        perms = [
            template_perm
            % {"app_label": model._meta.app_label, "model_name": model._meta.model_name}
            for template_perm in template_perms
        ]
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


class FormUpdateView(PermissionRequiredByHttpMethodMixin, DetailView):
    method = "PUT"


class FormCreateView(PermissionRequiredByHttpMethodMixin, TemplateView):
    method = "POST"


def rest_exception_handler(exc, context):
    request = context.get("request")
    logger.warning("DRF exception handler %s", exc, exc_info=True)
    if request and request.accepted_media_type == "text/html":
        if isinstance(exc, (Http404, NotFound)):
            return page_not_found(request, exc, context=context)
        elif isinstance(exc, (PermissionDenied, DrfPermissionDenied, NotAuthenticated)):
            return permission_denied(request, exc, context=context)
        elif isinstance(exc, APIException) and 400 <= exc.status_code <= 500:
            return other_400_error(request, exc, context=context)
        else:
            return server_error(request, context=context)
    else:
        return exception_handler(exc, context)


def permission_denied(request, exception, template_name="403.jinja", context=None):
    response = render(
        request=request, template_name=template_name, context=context, status=403
    )
    return response


def page_not_found(request, exception, template_name="404.jinja", context=None):
    response = render(
        request=request, template_name=template_name, context=context, status=404
    )
    return response


def other_400_error(request, exception, template_name="other_400.jinja", context=None):
    if context is None:
        context = {}
    context["description"] = (
        "Method Not Allowed" if exception.status_code == 405 else "Other error"
    )
    context["status"] = exception.status_code
    response = render(
        request=request,
        template_name=template_name,
        context=context,
        status=exception.status_code,
    )
    return response


def server_error(request, template_name="500.jinja", context=None):
    response = render(
        request=request, template_name=template_name, context=context, status=500
    )
    return response


class SmallResultSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 200

    @staticmethod
    def _to_search_terms(query_params):
        return [f"{k}: {v}" for k, v in query_params.lists()]

    def get_paginated_response(self, data):
        context = self.get_context_data(data)
        return Response(context)

    @classmethod
    def create_paginated_context_data(
        cls, query, data, current_page_number, count, query_params, size=None
    ):
        if size is None:
            size = cls.page_size
        # ceiling division https://stackoverflow.com/questions/14822184/is-there-a-ceiling-equivalent-of-operator-in-python
        num_pages = -(-count // size)
        page_range = list(
            range(
                max(2, current_page_number - 3), min(num_pages, current_page_number + 4)
            )
        )
        return OrderedDict(
            {
                "is_first_page": current_page_number == 1,
                "is_last_page": current_page_number == num_pages,
                "current_page": current_page_number,
                "num_results": min(size, count - (current_page_number - 1) * size),
                "count": count,
                "query": query,
                "search_terms": cls._to_search_terms(query_params),
                "query_params": query_params.urlencode(),
                "range": page_range,
                "num_pages": num_pages,
                "results": data,
            }
        )

    def get_context_data(self, data):
        query_params = self.request.query_params.copy()
        query = query_params.get("query")
        page = query_params.pop("page", [1])[0]
        count = self.page.paginator.count
        try:
            current_page_number = max(1, int(page))
        except ValueError:
            current_page_number = 1
        return self.create_paginated_context_data(
            query=query,
            data=data,
            current_page_number=current_page_number,
            count=count,
            query_params=query_params,
        )


@login_required
def discourse_sso(request):
    """
    Code adapted from https://meta.discourse.org/t/sso-example-for-django/14258
    """
    payload = request.GET.get("sso")
    signature = request.GET.get("sig")

    if None in [payload, signature]:
        return HttpResponseBadRequest(
            "No SSO payload or signature. Please contact us if this problem persists."
        )

    # Validate the payload

    payload = bytes(parse.unquote(payload), encoding="utf-8")
    decoded = base64.decodebytes(payload).decode("utf-8")
    if len(payload) == 0 or "nonce" not in decoded:
        return HttpResponseBadRequest(
            "Invalid payload. Please contact us if this problem persists."
        )

    key = bytes(settings.DISCOURSE_SSO_SECRET, encoding="utf-8")  # must not be unicode
    h = hmac.new(key, payload, digestmod=hashlib.sha256)
    this_signature = h.hexdigest()

    if not hmac.compare_digest(this_signature, signature):
        return HttpResponseBadRequest(
            "Invalid payload. Please contact us if this problem persists."
        )

    # Build the return payload
    qs = parse.parse_qs(decoded)
    user = request.user
    # FIXME: create a sync endpoint to sync up admins and groups (e.g., CoMSES full member Discourse group)
    # See https://meta.discourse.org/t/official-single-sign-on-for-discourse-sso/13045
    # for full description of params that can be added
    params = {
        "nonce": qs["nonce"][0],
        "email": user.email,
        "external_id": user.id,
        "username": user.member_profile.discourse_username,
        "require_activation": "false",
        "name": user.get_full_name(),
    }
    # add an avatar_url to the params if the user has one
    avatar_url = user.member_profile.avatar_url
    if avatar_url:
        params.update(avatar_url=request.build_absolute_uri(avatar_url))

    return_payload = base64.encodebytes(bytes(parse.urlencode(params), "utf-8"))
    h = hmac.new(key, return_payload, digestmod=hashlib.sha256)
    query_string = parse.urlencode({"sso": return_payload, "sig": h.hexdigest()})

    # Redirect back to Discourse
    discourse_sso_url = build_discourse_url(f"session/sso_login?{query_string}")
    return HttpResponseRedirect(discourse_sso_url)


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


class NoDeleteNoUpdateViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    pass


class HtmlNoDeleteNoUpdateViewSet(
    mixins.CreateModelMixin,
    HtmlListModelMixin,
    HtmlRetrieveModelMixin,
    viewsets.GenericViewSet,
):
    pass


class NoDeleteViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    pass


class HtmlNoDeleteViewSet(
    mixins.CreateModelMixin,
    HtmlListModelMixin,
    HtmlRetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    pass


class OnlyObjectPermissionModelViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    pass


class HtmlOnlyObjectPermissionModelViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    HtmlListModelMixin,
    HtmlRetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    pass
