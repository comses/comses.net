import base64
import binascii
import hashlib
import hmac
import logging
from urllib import parse

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.images import ImageFile
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import (
    Http404,
    HttpResponseBadRequest,
    HttpResponseRedirect,
    HttpResponseServerError,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET
from django.views.generic import DetailView, TemplateView, RedirectView
from django.urls import reverse
from rest_framework import (
    viewsets,
    generics,
    parsers,
    mixins,
    filters,
)
from rest_framework.exceptions import (
    PermissionDenied as DrfPermissionDenied,
    NotAuthenticated,
    NotFound,
    APIException,
)
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView, exception_handler
from taggit.models import Tag
from wagtail.images.models import Image

from library.models import Codebase
from .models import ComsesGroups, Event, FollowUser, Job, MemberProfile
from .serializers import (
    EventSerializer,
    JobSerializer,
    MemberProfileSerializer,
    RelatedMemberProfileSerializer,
    TagSerializer,
)
from .mixins import (
    CommonViewSetMixin,
    HtmlListModelMixin,
    HtmlRetrieveModelMixin,
    PermissionRequiredByHttpMethodMixin,
    SpamCatcherViewSetMixin,
)
from .pagination import SmallResultSetPagination
from .permissions import ObjectPermissions, ViewRestrictedObjectPermissions
from .view_helpers import (
    add_user_retrieve_perms,
    get_search_queryset,
    retrieve_with_perms,
)
from .utils import parse_date, parse_datetime

logger = logging.getLogger(__name__)

INVALID_SSO_PAYLOAD = "Invalid payload. Please contact us if this problem persists."
SSO_NONCE_TTL_SECONDS = 10 * 60


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


class FormUpdateView(PermissionRequiredByHttpMethodMixin, DetailView):
    method = "PUT"


class FormCreateView(PermissionRequiredByHttpMethodMixin, TemplateView):
    method = "POST"


class FormMarkDeletedView(PermissionRequiredByHttpMethodMixin, DetailView):
    method = "DELETE"

    def post(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()
        return redirect(instance.get_list_url())


def make_error(request, should_raise=True):
    if should_raise:
        raise ValueError("This is an unhandled error")
    return HttpResponseServerError("This is an unhandled server error response.")


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


def is_sso_secret_configured(secret):
    return bool(secret) and secret != "unconfigured"


class SsoVerificationError(SuspiciousOperation):
    """Raised when an SSO handshake fails protocol verification."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


def verify_sso_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected_signature = hmac.new(
        secret.encode("utf-8"), payload, digestmod=hashlib.sha256
    ).hexdigest()
    try:
        signature_bytes = signature.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return hmac.compare_digest(expected_signature.encode("utf-8"), signature_bytes)


def decode_sso_payload(payload: bytes):
    try:
        decoded = base64.decodebytes(payload).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None
    qs = parse.parse_qs(decoded)
    if "nonce" not in qs:
        return None
    return qs


def check_and_consume_sso_nonce(nonce: str, namespace: str) -> bool:
    digest = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
    # Ten minutes covers normal login round trips while bounding cache growth and
    # replay windows.
    return cache.add(
        f"sso:{namespace}:consumed_nonce:{digest}", True, SSO_NONCE_TTL_SECONDS
    )


def build_signed_sso_redirect(
    base_url: str, path: str, params: dict, secret: str
) -> str:
    return_payload = base64.encodebytes(bytes(parse.urlencode(params), "utf-8"))
    signature = hmac.new(
        secret.encode("utf-8"), return_payload, digestmod=hashlib.sha256
    ).hexdigest()
    query_string = parse.urlencode({"sso": return_payload, "sig": signature})
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}?{query_string}"


def get_verified_sso_payload(request, secret: str):
    # Reject duplicate sso or sig parameters to prevent parameter smuggling
    if len(request.GET.getlist("sso")) > 1 or len(request.GET.getlist("sig")) > 1:
        raise SsoVerificationError(
            "Duplicate SSO parameters detected. Please contact us if this problem persists."
        )

    payload = request.GET.get("sso")
    signature = request.GET.get("sig")

    if not payload or not signature:
        raise SsoVerificationError(
            "No SSO payload or signature. Please contact us if this problem persists."
        )

    payload = bytes(parse.unquote(payload), encoding="utf-8")
    if not verify_sso_signature(payload, signature, secret):
        raise SsoVerificationError(INVALID_SSO_PAYLOAD)

    qs = decode_sso_payload(payload)
    if qs is None:
        raise SsoVerificationError(INVALID_SSO_PAYLOAD)

    return qs


@login_required
@require_GET
def discourse_sso(request):
    """
    Code adapted from https://meta.discourse.org/t/sso-example-for-django/14258
    """
    if not is_sso_secret_configured(settings.DISCOURSE_SSO_SECRET):
        raise Http404("The Discourse integration is not configured")

    try:
        qs = get_verified_sso_payload(request, settings.DISCOURSE_SSO_SECRET)
    except SsoVerificationError as e:
        return HttpResponseBadRequest(e.message)

    # Build the return payload
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

    if not check_and_consume_sso_nonce(qs["nonce"][0], "discourse"):
        return HttpResponseBadRequest(INVALID_SSO_PAYLOAD)

    # Redirect back to Discourse
    return HttpResponseRedirect(
        build_signed_sso_redirect(
            settings.DISCOURSE_BASE_URL,
            "session/sso_login",
            params,
            settings.DISCOURSE_SSO_SECRET,
        )
    )


@login_required
@require_GET
def librarian_sso(request):
    """
    Single sign-on provider for the CoMSES Librarian, mirroring discourse_sso above.

    The Librarian mints its own session from the signed claims returned here, so this view is the
    only place group membership is established. Three deliberate differences from discourse_sso:

    - the signature is verified before the payload is decoded, so malformed base64 or non-utf-8
      plaintext returns 400 rather than raising past the handler
    - `nonce` is checked as a parsed query parameter rather than as a substring of the decoded
      payload, which is what the return payload actually needs
    - access is restricted to the "Librarian Users" group and refused with an explanatory page

    `groups` is filtered to ComsesGroups values rather than taken from user.groups, keeping it a
    closed admin-managed set with no substring collisions.
    """
    if not settings.LIBRARIAN_BASE_URL or not is_sso_secret_configured(
        settings.LIBRARIAN_SSO_SECRET
    ):
        # an empty secret is never a state to sign from
        raise Http404("The CoMSES Librarian integration is not configured")

    try:
        qs = get_verified_sso_payload(request, settings.LIBRARIAN_SSO_SECRET)
    except SsoVerificationError as e:
        return HttpResponseBadRequest(e.message)

    user = request.user
    if not ComsesGroups.LIBRARIAN.is_member(user):
        logger.info("refused librarian sso for non-member user %s", user.pk)
        return permission_denied(
            request, None, template_name="core/librarian_sso_denied.jinja"
        )

    member_group_names = set(user.groups.values_list("name", flat=True))
    params = {
        "nonce": qs["nonce"][0],
        "external_id": user.pk,
        "email": user.email,
        "username": user.username,
        "name": user.get_full_name(),
        "groups": ",".join(
            g.value for g in ComsesGroups if g.value in member_group_names
        ),
        # convenience for the Librarian's logs; non-members are refused above and it performs its
        # own exact-match check against `groups` regardless
        "is_librarian_user": "true",
    }

    if not check_and_consume_sso_nonce(qs["nonce"][0], "librarian"):
        return HttpResponseBadRequest(INVALID_SSO_PAYLOAD)

    # the callback is configured server-side and never taken from the request, otherwise any
    # signed payload could aim this endpoint anywhere
    return HttpResponseRedirect(
        build_signed_sso_redirect(
            settings.LIBRARIAN_BASE_URL,
            "auth/sso/callback",
            params,
            settings.LIBRARIAN_SSO_SECRET,
        )
    )


class ProfileRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False
    query_string = False

    def get_redirect_url(self, *args, **kwargs):
        return reverse("core:profile-detail", kwargs={"pk": self.request.user.id})


class ToggleFollowUser(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        logger.debug("POST with request data: %s", request.data)
        username = request.data["username"]
        source = request.user
        target = User.objects.get(username=username)
        follow_user, created = FollowUser.objects.get_or_create(
            source=source, target=target
        )
        if created:
            target.following.add(follow_user)
        else:
            follow_user.delete()
        return Response({"following": created})


class TagListView(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = TagSerializer
    queryset = Tag.objects.all()
    pagination_class = SmallResultSetPagination
    permission_classes = (AllowAny,)

    def get_queryset(self):
        query = self.request.query_params.get("query")
        queryset = Tag.objects.all()
        if query:
            queryset = queryset.filter(name__icontains=query)
        return queryset.order_by("name")


class MemberProfileFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if view.action != "list":
            return queryset
        query_params = request.query_params
        tags = query_params.getlist("tags")
        return get_search_queryset(query_params, queryset, tags=tags)


class MemberProfileViewSet(CommonViewSetMixin, HtmlNoDeleteViewSet):
    lookup_field = "user__pk"
    lookup_url_kwarg = "pk"
    queryset = MemberProfile.objects.public().with_tags()
    pagination_class = SmallResultSetPagination
    filter_backends = (MemberProfileFilter,)
    permission_classes = (ObjectPermissions,)
    context_object_name = "profile"
    context_list_name = "profiles"

    def get_serializer_class(self):
        if self.action == "list":
            return RelatedMemberProfileSerializer
        else:
            return MemberProfileSerializer

    def get_queryset(self):
        if self.action == "retrieve":
            return self.queryset.with_peer_review_invitations()
        else:
            return self.queryset.with_user()

    def get_retrieve_context(self, instance):
        context = super().get_retrieve_context(instance)
        accessing_user = self.request.user
        logger.debug("Finding models for user %s", instance.user)
        context["codebases"] = (
            Codebase.objects.accessible(accessing_user)
            .filter_by_contributor_or_submitter(instance.user)
            .with_tags()
            .with_featured_images()
            .order_by("-last_modified")
        )
        add_user_retrieve_perms(instance, context, accessing_user)
        return context


class MemberProfileImageUploadView(generics.CreateAPIView):
    parser_classes = (
        parsers.MultiPartParser,
        parsers.FormParser,
    )
    queryset = MemberProfile.objects.all()

    def create(self, request, *args, **kwargs):
        file_obj = request.data["file"]
        member_profile = get_object_or_404(MemberProfile, **kwargs)
        # FIXME: perform validity checks on the file_obj (jpg, png, etc only)
        image = Image.objects.create(
            title=file_obj.name, file=ImageFile(file_obj), uploaded_by_user=request.user
        )
        member_profile.picture = image
        member_profile.save()
        return Response(data=image.get_rendition("fill-150x150").url, status=200)


class ProfileUpdateView(FormUpdateView):
    model = MemberProfile
    slug_field = "user__pk"
    slug_url_kwarg = "user__pk"


class EventCreateView(FormCreateView):
    model = Event


class EventUpdateView(FormUpdateView):
    model = Event


class EventMarkDeletedView(FormMarkDeletedView):
    model = Event


class JobCreateView(FormCreateView):
    model = Job


class JobUpdateView(FormUpdateView):
    model = Job


class JobMarkDeletedView(FormMarkDeletedView):
    model = Job


class EventFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if view.action != "list":
            return queryset
        query_params = request.query_params
        logger.debug("query params %s", query_params)
        submission_deadline__gte = parse_date(
            query_params.get("submission_deadline__gte")
            or query_params.get("submission_deadline_after")
        )
        start_date__gte = parse_date(
            query_params.get("start_date__gte") or query_params.get("start_date_after")
        )
        tags = request.query_params.getlist("tags")

        criteria = {}

        if submission_deadline__gte:
            criteria.update(submission_deadline__gte=submission_deadline__gte)
        if start_date__gte:
            criteria.update(start_date__gte=start_date__gte)
        return get_search_queryset(
            query_params,
            queryset,
            tags=tags,
            criteria=criteria,
        )


class EventViewSet(
    SpamCatcherViewSetMixin, CommonViewSetMixin, OnlyObjectPermissionModelViewSet
):
    serializer_class = EventSerializer
    queryset = (
        Event.objects.with_tags()
        .with_submitter()
        .with_expired()
        .with_started()
        .order_by("-date_created")
    )
    pagination_class = SmallResultSetPagination
    filter_backends = (OrderingFilter, EventFilter)
    permission_classes = (ViewRestrictedObjectPermissions,)
    ordering_fields = (
        "date_created",
        "last_modified",
        "early_registration_deadline",
        "submission_deadline",
        "start_date",
    )

    def get_queryset(self):
        return self.queryset.public()

    def retrieve(self, request, *args, **kwargs):
        return retrieve_with_perms(self, request, *args, **kwargs)

    def get_calendar_queryset(self):
        start = parse_date(self.request.query_params["start"])
        end = parse_date(self.request.query_params["end"])
        return self.queryset.public().find_by_interval(start, end), start, end

    @staticmethod
    def to_calendar_early_registration_deadline_event(event):
        return {
            "title": "Early Registration Deadline: " + event.title,
            "start": event.early_registration_deadline.isoformat(),
            "url": event.get_absolute_url(),
            "color": "#D9230F",
        }

    @staticmethod
    def to_calendar_submission_deadline_event(event):
        return {
            "title": "Submission Deadline: " + event.title,
            "start": event.submission_deadline.isoformat(),
            "url": event.get_absolute_url(),
            "color": "#D9230F",
        }

    @staticmethod
    def to_calendar_event(event):
        return {
            "title": event.title,
            "start": event.start_date.isoformat(),
            "end": event.end_date.isoformat(),
            "url": event.get_absolute_url(),
            "color": "#3a87ad",
        }

    @action(detail=False)
    def calendar(self, request, *args, **kwargs):
        """Arrange events so that early registration deadline, registration deadline and the actual event
        are events to be rendered in the calendar"""
        calendar_events = {}
        if request.query_params:
            if request.accepted_media_type == "application/json":
                calendar_events = []
                queryset, start, end = self.get_calendar_queryset()
                for event in list(queryset):
                    if (
                        event.early_registration_deadline
                        and start <= event.early_registration_deadline <= end
                    ):
                        calendar_events.append(
                            self.to_calendar_early_registration_deadline_event(event)
                        )

                    if (
                        event.submission_deadline
                        and start <= event.submission_deadline <= end
                    ):
                        calendar_events.append(
                            self.to_calendar_submission_deadline_event(event)
                        )

                    if event.start_date:
                        min_date = max(start, event.start_date)
                        if event.end_date is None:
                            event.end_date = event.start_date
                        max_date = min(end, event.end_date)
                        if min_date <= max_date:
                            calendar_events.append(self.to_calendar_event(event))
            else:
                # FIXME: revert if this turns out to be a terrible idea
                return redirect(
                    reverse("core:event-list")
                    + "?{0}".format(request.query_params.urlencode())
                )

        return Response(
            data=calendar_events, template_name="core/events/calendar.jinja"
        )


class JobFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if view.action != "list":
            return queryset
        query_params = request.query_params
        date_created = parse_datetime(
            query_params.get("date_created__gte")
            or query_params.get("date_created_after")
        )
        application_deadline = parse_date(
            query_params.get("application_deadline__gte")
            or query_params.get("application_deadline_after")
        )
        tags = query_params.getlist("tags")
        criteria = {}
        if date_created:
            criteria.update(date_created__gte=date_created)
        if application_deadline:
            criteria.update(application_deadline__gte=application_deadline)
        return get_search_queryset(query_params, queryset, tags=tags, criteria=criteria)


class JobViewSet(
    SpamCatcherViewSetMixin, CommonViewSetMixin, OnlyObjectPermissionModelViewSet
):
    serializer_class = JobSerializer
    pagination_class = SmallResultSetPagination
    queryset = (
        Job.objects.with_tags()
        .with_submitter()
        .with_expired()
        .order_by("-date_created")
    )
    filter_backends = (OrderingFilter, JobFilter)
    permission_classes = (ViewRestrictedObjectPermissions,)
    ordering_fields = (
        "application_deadline",
        "date_created",
        "last_modified",
    )

    def get_queryset(self):
        # exclude spam from list view
        if self.action == "list":
            return self.queryset.public()
        return self.queryset

    def retrieve(self, request, *args, **kwargs):
        return retrieve_with_perms(self, request, *args, **kwargs)
