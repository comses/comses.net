import base64
import hashlib
import hmac
import logging
from urllib import parse
from dateutil import tz

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.files.images import ImageFile
from django.db.models.query_utils import Q
from django.http import QueryDict, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework import viewsets, generics, parsers, status, mixins, filters
from rest_framework.decorators import detail_route, list_route
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from taggit.models import Tag
from wagtail.wagtailimages.models import Image
from wagtail.wagtailsearch.backends import get_search_backend

from core.views import FormViewSetMixin, FormCreateView, FormUpdateView
from core.view_helpers import get_search_queryset, retrieve_with_perms
from core.utils import parse_datetime
from .models import FeaturedContentItem, MemberProfile
from core.models import FollowUser, Event, Job
from .serializers import (EventSerializer, JobSerializer, TagSerializer, FeaturedContentItemSerializer,
                          MemberProfileSerializer, UserMessageSerializer)
from .common_serializers import RelatedMemberProfileSerializer

logger = logging.getLogger(__name__)

search = get_search_backend()


class SmallResultSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 200

    def get_paginated_response(self, data, **kwargs):
        query_params = QueryDict('', mutable=True)

        query = self.request.query_params.get('query')
        if query:
            query_params['query'] = query
        tags = self.request.query_params.getlist('tags')
        if tags:
            query_params['tags'] = tags
        order_by = self.request.query_params.getlist('order_by')
        if order_by:
            query_params['order_by'] = order_by

        count = self.page.paginator.count
        n_pages = count // self.page_size + 1
        page = int(self.request.query_params.get('page', 1))
        return Response({
            'current_page': page,
            'count': count,
            'query': self.request.query_params.get('query'),
            'query_params': query_params.urlencode(),
            'range': list(range(max(1, page - 4), min(n_pages + 1, page + 5))),
            'n_pages': n_pages,
            'results': data
        }, **kwargs)


@login_required
def discourse_sso(request):
    '''
    Code adapted from https://meta.discourse.org/t/sso-example-for-django/14258
    '''
    payload = request.GET.get('sso')
    signature = request.GET.get('sig')

    if None in [payload, signature]:
        return HttpResponseBadRequest('No SSO payload or signature. Please contact support if this problem persists.')

    # Validate the payload

    payload = bytes(parse.unquote(payload), encoding='utf-8')
    decoded = base64.decodebytes(payload).decode('utf-8')
    if len(payload) == 0 or 'nonce' not in decoded:
        return HttpResponseBadRequest('Invalid payload. Please contact support if this problem persists.')

    key = bytes(settings.DISCOURSE_SSO_SECRET, encoding='utf-8')  # must not be unicode
    h = hmac.new(key, payload, digestmod=hashlib.sha256)
    this_signature = h.hexdigest()

    if this_signature != signature:
        return HttpResponseBadRequest('Invalid payload. Please contact support if this problem persists.')

    # Build the return payload
    qs = parse.parse_qs(decoded)
    user = request.user
    # FIXME: create a sync endpoint to sync up admins and groups (e.g., CoMSES full member Discourse group)
    params = {
        'nonce': qs['nonce'][0],
        'email': user.email,
        'external_id': user.id,
        'username': user.username,
        'require_activation': 'false',
        'name': user.get_full_name(),
    }

    return_payload = base64.encodebytes(bytes(parse.urlencode(params), 'utf-8'))
    h = hmac.new(key, return_payload, digestmod=hashlib.sha256)
    query_string = parse.urlencode({'sso': return_payload, 'sig': h.hexdigest()})

    # Redirect back to Discourse
    discourse_sso_url = '{0}/session/sso_login?{1}'.format(settings.DISCOURSE_BASE_URL, query_string)
    return HttpResponseRedirect(discourse_sso_url)


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


class EventFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if view.action != 'list':
            return queryset

        q = request.query_params.get('query')
        submission_deadline__gte = request.query_params.get('submission_deadline__gte')
        event_start_date__gte = parse_datetime(request.query_params.get('event_state_date__gte'))
        tags = request.query_params.get('tags', [])

        if submission_deadline__gte:
            queryset = queryset.filter(submission_deadline__gte=submission_deadline__gte)
        if event_start_date__gte:
            queryset = queryset.filter(event_start_date__gte=event_start_date__gte)
        for tag in tags:
            queryset = queryset.filter(tags__name=tag)

        if q:
            queryset = get_search_queryset(q, queryset)
        else:
            queryset = queryset.order_by('-date_created')

        return queryset


class EventViewSet(FormViewSetMixin, viewsets.ModelViewSet):
    serializer_class = EventSerializer
    queryset = Event.objects.all()
    pagination_class = SmallResultSetPagination
    filter_backends = (EventFilter,)

    def get_queryset(self):
        return self.queryset

    def retrieve(self, request, *args, **kwargs):
        return retrieve_with_perms(self, request, *args, **kwargs)


class EventCalendarList(generics.ListAPIView):
    queryset = Event.objects.all()
    # FIXME: refactor this and other apps, https://github.com/comses/core.comses.net/issues/118
    template_name = 'core/events/calendar.jinja'

    def get_list_queryset(self):
        start = parse_datetime(self.request.query_params['start'])
        end = parse_datetime(self.request.query_params['end'])

        # push this into EventQuerySet
        early_registration_deadline_queryset = self.queryset.filter(
            Q(early_registration_deadline__gte=start) & Q(early_registration_deadline__lte=end))
        submission_deadline_queryset = self.queryset.filter(
            Q(submission_deadline__gte=start) & Q(submission_deadline__lte=end))
        queryset = self.queryset.exclude(Q(start_date__gte=end)).exclude(
            Q(end_date__lte=start))
        queryset = queryset | early_registration_deadline_queryset | submission_deadline_queryset
        return queryset, start, end

    @staticmethod
    def to_calendar_early_registration_deadline_event(event):
        return {
            'title': 'Early Registration Deadline: ' + event.title,
            'start': event.early_registration_deadline.isoformat(),
            'url': event.get_absolute_url(),
            'color': '#aaa',
        }

    @staticmethod
    def to_calendar_submission_deadline_event(event):
        return {
            'title': 'Submission Deadline: ' + event.title,
            'start': event.submission_deadline.isoformat(),
            'url': event.get_absolute_url(),
            'color': '#ccc',
        }

    @staticmethod
    def to_calendar_event(event):
        return {
            'title': event.title,
            'start': event.start_date.isoformat(),
            'end': event.end_date.isoformat(),
            'url': event.get_absolute_url(),
            'color': '#92c02e',
        }

    def list(self, request, *args, **kwargs):
        """Arrange events so that early registration deadline, registration deadline and the actual event
        are events to be rendered in the calendar"""

        if not request.query_params:
            return Response(data={})

        queryset, start, end = self.get_list_queryset()
        calendar_events = []
        for event in list(queryset):
            if event.early_registration_deadline and start <= event.early_registration_deadline <= end:
                calendar_events.append(self.to_calendar_early_registration_deadline_event(event))

            if event.submission_deadline and start <= event.submission_deadline <= end:
                calendar_events.append(self.to_calendar_submission_deadline_event(event))

            if event.start_date and not (event.start_date > end or event.end_date < start):
                calendar_events.append(self.to_calendar_event(event))

        return Response(data=calendar_events)


class JobFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if view.action != 'list':
            return queryset
        q = request.query_params.get('query')
        date_created__gte = parse_datetime(request.query_params.get('date_created__gte'))
        last_modified__gte = parse_datetime(request.query_params.get('last_modified__gte'))
        tags = request.query_params.get('tags', [])

        if date_created__gte:
            queryset = queryset.filter(date_created__gte=date_created__gte)
        if last_modified__gte:
            queryset = queryset.filter(last_modified__gte=last_modified__gte)
        for tag in tags:
            queryset = queryset.filter(tags__name=tag)

        if q:
            queryset = get_search_queryset(q, queryset)
        else:
            queryset = queryset.order_by('-date_created')

        return queryset


class JobViewSet(FormViewSetMixin, viewsets.ModelViewSet):
    serializer_class = JobSerializer
    pagination_class = SmallResultSetPagination
    queryset = Job.objects.all()
    filter_backends = (JobFilter,)

    def get_queryset(self):
        return self.queryset

    def retrieve(self, request, *args, **kwargs):
        return retrieve_with_perms(self, request, *args, **kwargs)


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    queryset = Tag.objects.all()
    pagination_class = SmallResultSetPagination

    @property
    def template_name(self):
        return 'home/tags/{}.jinja'.format(self.action)

    def get_queryset(self):
        query = self.request.query_params.get('query')
        queryset = Tag.objects.all()
        if query:
            queryset = queryset.filter(name__icontains=query)
        return queryset.order_by('name')


class ProfileViewSet(FormViewSetMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,
                     mixins.UpdateModelMixin, viewsets.GenericViewSet):
    lookup_field = 'user__username'
    lookup_url_kwarg = 'username'
    lookup_value_regex = '[\w\.\-@]+'
    serializer_class = MemberProfileSerializer
    queryset = MemberProfile.objects.with_institution()
    pagination_class = SmallResultSetPagination

    def get_queryset(self):
        # make sort order parameterizable. Start with ID or last_name? Lots of spam users visible with
        # last_name / username
        query = self.request.query_params.get('query')
        queryset = self.queryset.public()
        queryset = queryset.order_by('id')
        if query:
            return queryset.filter(user__username__startswith=query)
        return queryset

    def retrieve(self, request, *args, **kwargs):
        return retrieve_with_perms(self, request, *args, **kwargs)

    @detail_route(methods=['post'])
    @method_decorator(login_required)
    def message(self, request, *args, **kwargs):
        logger.debug("POST with request data: %s", request.data)
        # FIXME: perhaps we should just send an email directly instead of caching in the db.
        serializer = UserMessageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @list_route(methods=['get'])
    def search(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = RelatedMemberProfileSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MemberProfileImageUploadView(generics.CreateAPIView):
    parser_classes = (parsers.MultiPartParser, parsers.FormParser,)
    queryset = MemberProfile.objects.all()

    def create(self, request, *args, **kwargs):
        file_obj = request.data['file']
        username = request.user.username
        member_profile = get_object_or_404(MemberProfile, user__username=username)
        image = Image(title=file_obj.name, file=ImageFile(file_obj), uploaded_by_user=request.user)
        image.save()
        member_profile.picture = image
        member_profile.save()
        return Response(data=image.get_rendition('fill-150x150').url, status=200)


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
    slug_field = 'user__username'
    slug_url_kwarg = 'username'
