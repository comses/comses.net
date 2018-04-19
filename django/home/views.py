import logging

import requests
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.images import ImageFile
from django.db.models import Prefetch
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, RedirectView
from rest_framework import viewsets, generics, parsers, status, mixins, renderers, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from taggit.models import Tag
from wagtail.images.models import Image
from wagtail.search.backends import get_search_backend

from core.models import FollowUser, Event, Job
from core.serializers import TagSerializer, EventSerializer, JobSerializer
from core.utils import parse_datetime
from core.view_helpers import retrieve_with_perms, get_search_queryset
from core.views import (CaseInsensitiveOrderingFilter, CommonViewSetMixin, FormCreateView, FormUpdateView,
                        SmallResultSetPagination)
from library.models import Codebase
from .models import FeaturedContentItem, MemberProfile, ContactPage
from .serializers import (FeaturedContentItemSerializer, UserMessageSerializer, MemberProfileSerializer,
                          MemberProfileListSerializer)

logger = logging.getLogger(__name__)

search = get_search_backend()


"""
Contains wagtail related views
"""


class ProfileRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False
    query_string = False

    def get_redirect_url(self, *args, **kwargs):
        return reverse('home:profile-detail', kwargs={'pk': self.request.user.pk})


class ToggleFollowUser(APIView):
    permission_classes = (IsAuthenticated,)
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer)

    def post(self, request, *args, **kwargs):
        logger.debug("POST with request data: %s", request.data)
        username = request.data['username']
        source = request.user
        target = User.objects.get(username=username)
        follow_user, created = FollowUser.objects.get_or_create(source=source, target=target)
        if created:
            target.following.add(follow_user)
        else:
            follow_user.delete()
        return Response({'following': created})


class TagListView(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = TagSerializer
    queryset = Tag.objects.all()
    pagination_class = SmallResultSetPagination
    renderer_classes = (renderers.JSONRenderer,)

    def get_queryset(self):
        query = self.request.query_params.get('query')
        queryset = Tag.objects.all()
        if query:
            queryset = queryset.filter(name__icontains=query)
        return queryset.order_by('name')


class MemberProfileFilter(filters.BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):
        if view.action != 'list':
            return queryset
        query_params = request.query_params
        qs = query_params.get('query')
        tags = query_params.getlist('tags')
        return get_search_queryset(qs, queryset, tags=tags)


class ProfileViewSet(CommonViewSetMixin,
                     mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                     viewsets.GenericViewSet):
    lookup_field = 'user__pk'
    lookup_url_kwarg = 'pk'
    queryset = MemberProfile.objects.public().with_tags().order_by('-user__date_joined')
    pagination_class = SmallResultSetPagination
    filter_backends = (CaseInsensitiveOrderingFilter, MemberProfileFilter)
    ordering_fields = ('user__date_joined', 'user__last_name', 'user__first_name',)

    def get_serializer_class(self):
        if self.action == 'list':
            return MemberProfileListSerializer
        return MemberProfileSerializer

    def get_queryset(self):
        if self.action == 'retrieve':
            return self.queryset.prefetch_related('institution').prefetch_related(
                Prefetch('user', User.objects.prefetch_related(
                    Prefetch('codebases', Codebase.objects.with_tags().with_featured_images()
                             .with_contributors(user=self.request.user).order_by('-date_created')))))
        return self.queryset.with_institution().with_user()

    def retrieve(self, request, *args, **kwargs):
        return retrieve_with_perms(self, request, *args, **kwargs)

    @action(detail=True, methods=['post'])
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
    parser_classes = (parsers.MultiPartParser, parsers.FormParser,)
    queryset = MemberProfile.objects.all()

    def create(self, request, *args, **kwargs):
        file_obj = request.data['file']
        member_profile = request.user.member_profile
        image = Image(title=file_obj.name, file=ImageFile(file_obj), uploaded_by_user=request.user)
        image.save()
        member_profile.picture = image
        member_profile.save()
        return Response(data=image.get_rendition('fill-150x150').url, status=200)


class ContactSentView(TemplateView):
    template_name = 'home/about/contact-sent.jinja'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['page'] = ContactPage.objects.first()
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
    slug_field = 'user__pk'
    slug_url_kwarg = 'user__pk'


class EventFilter(filters.BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):
        if view.action != 'list':
            return queryset
        query_string = request.query_params.get('query')
        query_params = request.query_params
        submission_deadline__gte = parse_datetime(query_params.get('submission_deadline__gte'))
        start_date__gte = parse_datetime(query_params.get('start_date__gte') or query_params.get('start_date'))
        tags = request.query_params.getlist('tags')

        criteria = {}

        if submission_deadline__gte:
            criteria.update(submission_deadline__gte=submission_deadline__gte)
        if start_date__gte:
            criteria.update(start_date__gte=start_date__gte)
        return get_search_queryset(query_string, queryset, tags=tags, criteria=criteria)


class EventViewSet(CommonViewSetMixin, viewsets.ModelViewSet):
    serializer_class = EventSerializer
    queryset = Event.objects.with_tags().with_submitter().order_by('-date_created', 'title')
    pagination_class = SmallResultSetPagination
    filter_backends = (CaseInsensitiveOrderingFilter, EventFilter)
    ordering_fields = ('date_created', 'last_modified',
                       'early_registration_deadline', 'submission_deadline', 'start_date',)

    def retrieve(self, request, *args, **kwargs):
        return retrieve_with_perms(self, request, *args, **kwargs)

    def get_calendar_queryset(self):
        start = parse_datetime(self.request.query_params['start'])
        end = parse_datetime(self.request.query_params['end'])
        return self.queryset.find_by_interval(start, end), start, end

    @staticmethod
    def to_calendar_early_registration_deadline_event(event):
        return {
            'title': 'Early Registration Deadline: ' + event.title,
            'start': event.early_registration_deadline.isoformat(),
            'url': event.get_absolute_url(),
            'color': '#D9230F',
        }

    @staticmethod
    def to_calendar_submission_deadline_event(event):
        return {
            'title': 'Submission Deadline: ' + event.title,
            'start': event.submission_deadline.isoformat(),
            'url': event.get_absolute_url(),
            'color': '#D9230F',
        }

    @staticmethod
    def to_calendar_event(event):
        return {
            'title': event.title,
            'start': event.start_date.isoformat(),
            'end': event.end_date.isoformat(),
            'url': event.get_absolute_url(),
            'color': '#3a87ad',
        }

    @action(detail=False)
    def calendar(self, request, *args, **kwargs):
        """Arrange events so that early registration deadline, registration deadline and the actual event
        are events to be rendered in the calendar"""
        calendar_events = {}
        if request.query_params:
            if request.accepted_media_type == 'application/json':
                calendar_events = []
                queryset, start, end = self.get_calendar_queryset()
                for event in list(queryset):
                    if event.early_registration_deadline and start <= event.early_registration_deadline <= end:
                        calendar_events.append(self.to_calendar_early_registration_deadline_event(event))

                    if event.submission_deadline and start <= event.submission_deadline <= end:
                        calendar_events.append(self.to_calendar_submission_deadline_event(event))

                    if event.start_date:
                        min_date = max(start, event.start_date)
                        if event.end_date is None:
                            event.end_date = event.start_date
                        max_date = min(end, event.end_date)
                        if min_date <= max_date:
                            calendar_events.append(self.to_calendar_event(event))
            else:
                # FIXME: revert if this turns out to be a terrible idea
                return redirect(reverse('home:event-list') + '?{0}'.format(request.query_params.urlencode()))

        return Response(data=calendar_events, template_name='core/events/calendar.jinja')


class JobFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if view.action != 'list':
            return queryset
        qs = request.query_params.get('query')
        date_created = parse_datetime(request.query_params.get('date_created__gte'))
        application_deadline = parse_datetime(request.query_params.get('application_deadline__gte'))
        tags = request.query_params.getlist('tags')
        criteria = {}
        if date_created:
            criteria.update(date_created__gte=date_created)
        if application_deadline:
            criteria.update(application_deadline__gte=application_deadline)
        return get_search_queryset(qs, queryset, tags=tags, criteria=criteria)


class JobViewSet(CommonViewSetMixin, viewsets.ModelViewSet):
    serializer_class = JobSerializer
    pagination_class = SmallResultSetPagination
    queryset = Job.objects.with_tags().with_submitter().order_by('-date_created')
    filter_backends = (CaseInsensitiveOrderingFilter, JobFilter)
    ordering_fields = ('application_deadline', 'date_created', 'last_modified', )

    def retrieve(self, request, *args, **kwargs):
        return retrieve_with_perms(self, request, *args, **kwargs)


class DigestView(TemplateView):
    template_name = 'home/digest.jinja'
    NUMBER_OF_POSTS = 20
    ARCHIVE_URL = 'http://comses.us7.list-manage.com/generate-js/?u=35f29299716fcb07509229c1c&fid=21449&show={0}'

    @property
    def mailchimp_archive_url(self):
        return self.ARCHIVE_URL.format(self.NUMBER_OF_POSTS)

    @property
    def _error_msg(self):
        return 'Unable to contact mailchimp archive url {0}'.format(self.mailchimp_archive_url)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data.setdefault('mailchimp_archives_js', 'document.write({})'.format(self._error_msg))
        try:
            cache_key = 'digest:js'
            mailchimp_archives_js = cache.get(cache_key)
            if not mailchimp_archives_js:
                response = requests.get(self.mailchimp_archive_url)
                mailchimp_archives_js = response.text  # a pile of document.writes
                cache.set(cache_key, mailchimp_archives_js, 86400)
            context_data['mailchimp_archives_js'] = mailchimp_archives_js
        except requests.exceptions.RequestException as e:
            logger.exception(e)
        return context_data
