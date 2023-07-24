import logging
import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.files.images import ImageFile
from django.http import QueryDict
from django.shortcuts import redirect, get_object_or_404
from django.template.loader import get_template
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, RedirectView, CreateView
from django.views.generic.list import ListView
from rest_framework import (
    viewsets,
    generics,
    parsers,
    status,
    mixins,
    renderers,
    filters,
)
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from taggit.models import Tag
from wagtail.images.models import Image

from core.models import FollowUser, Event, Job
from core.permissions import ObjectPermissions, ViewRestrictedObjectPermissions
from core.serializers import TagSerializer, EventSerializer, JobSerializer
from core.utils import parse_datetime, send_markdown_email
from core.view_helpers import (
    retrieve_with_perms,
    get_search_queryset,
    add_change_delete_perms,
)
from core.views import (
    CommonViewSetMixin,
    FormCreateView,
    FormUpdateView,
    SmallResultSetPagination,
    OnlyObjectPermissionModelViewSet,
    HtmlNoDeleteViewSet,
)
from library.models import Codebase
from .forms import ConferenceSubmissionForm
from .metrics import Metrics
from .models import (
    ComsesDigest,
    FeaturedContentItem,
    MemberProfile,
    ContactPage,
    ConferencePage,
)
from .serializers import (
    FeaturedContentItemSerializer,
    UserMessageSerializer,
    MemberProfileSerializer,
)
from .search import GeneralSearch


logger = logging.getLogger(__name__)

"""
Contains wagtail related views
"""


class ProfileRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False
    query_string = False

    def get_redirect_url(self, *args, **kwargs):
        return reverse("home:profile-detail", kwargs={"pk": self.request.user.pk})


class ToggleFollowUser(APIView):
    permission_classes = (IsAuthenticated,)
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer)

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
    renderer_classes = (renderers.JSONRenderer,)
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
        qs = query_params.get("query")
        tags = query_params.getlist("tags")
        return get_search_queryset(qs, queryset, tags=tags)


# FIXME: rename to MemberProfileViewSet
class ProfileViewSet(CommonViewSetMixin, HtmlNoDeleteViewSet):
    lookup_field = "user__pk"
    lookup_url_kwarg = "pk"
    queryset = MemberProfile.objects.public().with_tags()
    pagination_class = SmallResultSetPagination
    filter_backends = (MemberProfileFilter,)
    permission_classes = (ObjectPermissions,)
    serializer_class = MemberProfileSerializer
    context_object_name = "profile"
    context_list_name = "profiles"

    def get_queryset(self):
        if self.action == "retrieve":
            # FIXME: queries like this should live in the MemberProfileQuerySet / models layer, not the view.
            return self.queryset.with_peer_review_invitations()
        else:
            return self.queryset.with_user()

    def get_retrieve_context(self, instance):
        context = super().get_retrieve_context(instance)
        accessing_user = self.request.user
        logger.debug("Finding models for user %s", instance.user)
        context["codebases"] = (
            Codebase.objects.accessible(accessing_user)
            .filter_by_contributor(instance.user)
            .with_tags()
            .with_featured_images()
        )
        add_change_delete_perms(instance, context, accessing_user)
        return context

    @action(detail=True, methods=["post"])
    @method_decorator(login_required)
    def message(self, request, *args, **kwargs):
        logger.debug("POST with request data: %s", request.data)
        # FIXME: perhaps we should just send an email directly instead of caching in the db.
        serializer = UserMessageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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


class ContactSentView(TemplateView):
    template_name = "home/about/contact-sent.jinja"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["page"] = ContactPage.objects.first()
        return context_data


class FeaturedContentListAPIView(generics.ListAPIView):
    serializer_class = FeaturedContentItemSerializer
    queryset = FeaturedContentItem.objects.all()
    pagination_class = SmallResultSetPagination


class EventCreateView(FormCreateView):
    model = Event


class EventUpdateView(FormUpdateView):
    model = Event


class JobCreateView(FormCreateView):
    model = Job


class JobUpdateView(FormUpdateView):
    model = Job


class ProfileUpdateView(FormUpdateView):
    model = MemberProfile
    slug_field = "user__pk"
    slug_url_kwarg = "user__pk"


class EventFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if view.action != "list":
            return queryset
        query_string = request.query_params.get("query")
        query_params = request.query_params
        submission_deadline__gte = parse_datetime(
            query_params.get("submission_deadline__gte")
        )
        start_date__gte = parse_datetime(
            query_params.get("start_date__gte") or query_params.get("start_date")
        )
        tags = request.query_params.getlist("tags")

        criteria = {}

        if submission_deadline__gte:
            criteria.update(submission_deadline__gte=submission_deadline__gte)
        if start_date__gte:
            criteria.update(start_date__gte=start_date__gte)
        return get_search_queryset(query_string, queryset, tags=tags, criteria=criteria)


class EventViewSet(CommonViewSetMixin, OnlyObjectPermissionModelViewSet):
    serializer_class = EventSerializer
    queryset = (
        Event.objects.upcoming().with_tags().with_submitter().order_by("-date_created")
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

    def retrieve(self, request, *args, **kwargs):
        return retrieve_with_perms(self, request, *args, **kwargs)

    def get_calendar_queryset(self):
        start = parse_datetime(self.request.query_params["start"])
        end = parse_datetime(self.request.query_params["end"])
        return self.queryset.find_by_interval(start, end), start, end

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
            "end": event.end_date.replace(hour=23).isoformat(),
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
                    reverse("home:event-list")
                    + "?{0}".format(request.query_params.urlencode())
                )

        return Response(
            data=calendar_events, template_name="core/events/calendar.jinja"
        )


class JobFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if view.action != "list":
            return queryset
        qs = request.query_params.get("query")
        date_created = parse_datetime(request.query_params.get("date_created__gte"))
        application_deadline = parse_datetime(
            request.query_params.get("application_deadline__gte")
        )
        tags = request.query_params.getlist("tags")
        criteria = {}
        if date_created:
            criteria.update(date_created__gte=date_created)
        if application_deadline:
            criteria.update(application_deadline__gte=application_deadline)
        return get_search_queryset(qs, queryset, tags=tags, criteria=criteria)


class JobViewSet(CommonViewSetMixin, OnlyObjectPermissionModelViewSet):
    serializer_class = JobSerializer
    pagination_class = SmallResultSetPagination
    queryset = (
        Job.objects.upcoming().with_tags().with_submitter().order_by("-date_created")
    )
    filter_backends = (OrderingFilter, JobFilter)
    permission_classes = (ViewRestrictedObjectPermissions,)
    ordering_fields = (
        "application_deadline",
        "date_created",
        "last_modified",
    )

    def retrieve(self, request, *args, **kwargs):
        return retrieve_with_perms(self, request, *args, **kwargs)


class MetricsView(TemplateView):
    template_name = "home/about/metrics.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        m = Metrics()
        metrics_data_json = json.dumps(m.get_all_data())
        context["metrics_data_json"] = metrics_data_json
        return context


class SearchView(TemplateView):
    template_name = "home/search.jinja"

    def get_context_data(self, **kwargs):
        search = GeneralSearch()
        context = super().get_context_data(**kwargs)

        query = self.request.GET.get("query")
        page = self.request.GET.get("page", 1)
        try:
            page = int(page)
        except ValueError:
            page = 1
        if query is not None:
            results, total = search.search(query, start=(page - 1) * 10)
        else:
            results, total = [], 0

        pagination_context = SmallResultSetPagination.create_paginated_context_data(
            query=query,
            data=results,
            current_page_number=page,
            count=total,
            query_params=QueryDict(query_string="query={}".format(query)),
        )
        context["__all__"] = pagination_context
        context.update(pagination_context)
        return context


class DigestView(ListView):
    template_name = "home/digest.jinja"
    model = ComsesDigest
    context_object_name = "digests"


class ConferenceSubmissionView(LoginRequiredMixin, CreateView):
    template_name = "home/conference/submission.jinja"
    form_class = ConferenceSubmissionForm

    @property
    def conference(self):
        if getattr(self, "_conference", None) is None:
            self._conference = ConferencePage.objects.get(slug=self.kwargs["slug"])
        return self._conference

    def get_success_url(self):
        return self.conference.url

    @property
    def submitter(self):
        return self.request.user.member_profile

    def conference_requirements(self):
        # returns a list of tuples of id/description
        return [
            ("videoLength", "The length of my submitted video is under 12 minutes."),
            # ('presentationLanguage', 'My presentation is in English.'),
            (
                "presentationTheme",
                "My presentation is related to the theme of this conference.",
            ),
            ("fullMemberProfile", "I have a current member profile page."),
        ]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["conference"] = self.conference
        ctx["submitter"] = self.submitter
        ctx["conference_requirements"] = self.conference_requirements()
        return ctx

    def form_valid(self, form):
        form.instance.submitter = self.submitter
        form.instance.conference = self.conference
        # send an email to editors
        self._send_email(
            form, submitter=form.instance.submitter, conference=form.instance.conference
        )
        return super().form_valid(form)

    def _send_email(self, form, submitter=None, conference=None):
        template = get_template("home/conference/email/notify.jinja")
        markdown_content = template.render(
            context={
                "form": form,
                "conference": conference,
                "submitter": submitter,
                "profile_url": self.request.build_absolute_uri(submitter.profile_url),
            }
        )
        send_markdown_email(
            subject="{0} presentation submission".format(conference.title),
            body=markdown_content,
            to=[submitter.email],
            bcc=[settings.SERVER_EMAIL],
        )

    def form_invalid(self, form):
        logger.debug("form was invalid: %s", form)
        response = super().form_invalid(form)
        logger.debug("invalid form response: %s", response)
        return response
