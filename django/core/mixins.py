import logging

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import SpamModeration
from .permissions import ViewRestrictedObjectPermissions

logger = logging.getLogger(__name__)


def _common_namespace_path(model):
    """
    converts a model class like library.CodebaseRelease to 'library/codebase_releases'
    """
    meta = model._meta
    app_label = meta.app_label
    model_label = meta.verbose_name_plural.replace(" ", "_")
    # FIXME: consider replacing this with a simpler default with less logic like
    # return model._meta.label_lower.replace('.', '/')
    # which would convert library.CodebaseRelease to library/codebaserelease
    return f"{app_label}/{model_label}"


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
            if hasattr(self, "queryset"):
                self.namespace = _common_namespace_path(self.queryset.model)
            elif hasattr(self, "model"):
                self.namespace = _common_namespace_path(self.model)
            else:
                logger.error(
                    "invalid mixin, no namespace, queryset or model set on self"
                )
        return self.namespace

    def get_template_names(self):
        namespace = self._get_namespace()
        file_ext = self.ext
        ts = self.templates
        if not ts:
            # FIXME: why is self.templates being initialized here instead of in __init__ ...
            for action in self.ALLOWED_ACTIONS:
                # by convention, templates should be named <action>.<file-ext> and discovered in TEMPLATE_DIRS under
                # `django/<app-name>/jinja2/<namespace>/<action>.<file_ext>`.
                ts[action] = [f"{namespace}/{action}.{file_ext}"]
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
    ext = "jinja"

    def get_template_names(self):
        # assumes any class using this mixin will have a model attribute and an edit.<ext>
        namespace = (
            self.namespace if self.namespace else _common_namespace_path(self.model)
        )
        file_ext = self.ext if self.ext else "jinja"
        return [f"{namespace}/edit.{file_ext}"]

    def get_required_permissions(self, request=None):
        perms = ViewRestrictedObjectPermissions.get_required_object_permissions(
            self.method, self.model
        )
        return perms

    def check_permissions(self):
        user = self.request.user
        # user.has_perms hasn't been called yet so django-guardian
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
    Retrieve a model instance. If renderer is html pass the instance to the template directly
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


class SpamCatcherSerializerMixin(serializers.Serializer):
    """
    sets a "spam_context" flag on the serializer context using some simple heuristics:
    - if the honeypot field (named "content") is filled in
    - if the time between the page being loaded and the form being submitted is less than
      SPAM_LIKELY_SECONDS_THRESHOLD

    Note: a serializer using this mixin that overrides the validate method must call
    super().validate(attrs) to chain the validation logic
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["content"] = serializers.CharField(
            required=False, allow_blank=True, write_only=True
        )
        self.fields["loaded_time"] = serializers.DateTimeField(required=False)

    def validate(self, attrs):
        super().validate(attrs)
        if attrs.get("content"):
            self.context["spam_context"] = self.format_spam_context(
                "honeypot",
                {
                    "field_name": "content",
                    "field_value": attrs["content"],
                },
            )
        else:
            self.check_form_submit_time(attrs)
        # remove so that the serializer doesn't attempt to save these fields
        for field in ["content", "loaded_time"]:
            attrs.pop(field, None)

        return attrs

    def check_form_submit_time(self, attrs):
        loaded_time = attrs.get("loaded_time")
        submit_time = timezone.now()
        if loaded_time and submit_time:
            elapsed = submit_time - loaded_time
            if elapsed.total_seconds() < settings.SPAM_LIKELY_SECONDS_THRESHOLD:
                self.context["spam_context"] = self.format_spam_context(
                    "form_submit_time", {"elapsed_seconds": elapsed.total_seconds()}
                )

    def format_spam_context(self, method: str, value: dict):
        return {
            "detection_method": method,
            "detection_details": value,
        }


class SpamCatcherViewSetMixin:
    """
    creates a SpamContent object on create and update if the spam_context
    flag is set by the serializer (see SpamCatcherSerializerMixin)
    """

    def perform_create(self, serializer: serializers.Serializer):
        super().perform_create(serializer)
        self.handle_spam_detection(serializer)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        self.handle_spam_detection(serializer)

    def _validate_content_object(self, instance):
        # make sure that the instance has a spam_moderation attribute as well as the
        # necessary fields for displaying the spam content in the admin
        required_fields = [
            "spam_moderation",
            "is_marked_spam",
            "get_absolute_url",
            "title",
        ]
        for field in required_fields:
            if not hasattr(instance, field):
                raise ValueError(
                    f"instance {instance} does not have a {field} attribute"
                )

    @action(detail=True, methods=["post"])
    def mark_spam(self, request, **kwargs):
        # consider adding notes field to the request
        # notes = request.data.get("notes")
        instance = self.get_object()
        self._validate_content_object(instance)
        content_type = ContentType.objects.get_for_model(type(instance))
        spam_moderation, created = SpamModeration.objects.get_or_create(
            content_type=content_type,
            object_id=instance.id,
            defaults={
                "status": SpamModeration.Status.SPAM,
                "detection_method": "manual",
                "reviewer": request.user,
            },
        )
        if not created:
            spam_moderation.status = SpamModeration.Status.SPAM
            spam_moderation.detection_method = "manual"
            spam_moderation.reviewer = request.user
            spam_moderation.save()
        # return Response({"message": "Successfully marked as spam!"}, status=status.HTTP_200_OK)
        return redirect(instance.get_list_url())

    def handle_spam_detection(self, serializer: serializers.Serializer):
        if "spam_context" in serializer.context:
            try:
                self._validate_content_object(serializer.instance)
                self._record_spam(
                    serializer.instance, serializer.context["spam_context"]
                )
            except ValueError as e:
                logger.warning("Cannot flag %s as spam: %s", serializer.instance, e)

    def _record_spam(self, instance, spam_context: dict):
        content_type = ContentType.objects.get_for_model(type(instance))
        # SpamModeration updates the content instance on save
        spam_moderation, created = SpamModeration.objects.get_or_create(
            content_type=content_type,
            object_id=instance.id,
            defaults={
                "status": SpamModeration.Status.UNREVIEWED,
                "detection_method": spam_context["detection_method"],
                "detection_details": spam_context["detection_details"],
            },
        )
        if not created:
            spam_moderation.status = SpamModeration.Status.UNREVIEWED
            spam_moderation.save()
