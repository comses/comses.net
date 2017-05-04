import base64
import hashlib
import hmac
import logging
from urllib import parse
from dateutil.parser import parse as datetime_parse
from dateutil import tz

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models.query_utils import Q
from django.views.generic import TemplateView
from django.http import QueryDict, HttpResponseBadRequest, HttpResponseRedirect
from rest_framework import viewsets, generics, mixins
from rest_framework.pagination import PageNumberPagination
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from taggit.models import Tag
from wagtail.wagtailsearch.backends import get_search_backend

from core.view_helpers import get_search_queryset, retrieve_with_perms
from .models import Event, Job, FeaturedContentItem
from .serializers import EventSerializer, EventCalendarSerializer, JobSerializer, TagSerializer, \
    FeaturedContentItemSerializer, UserSerializer

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


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    queryset = Event.objects.all()
    pagination_class = SmallResultSetPagination

    def get_queryset(self):
        return get_search_queryset(self)

    @property
    def template_name(self):
        return 'home/events/{}.jinja'.format(self.action)

    def retrieve(self, request, *args, **kwargs):
        return retrieve_with_perms(self, request, *args, **kwargs)


class EventCalendarList(generics.ListAPIView):
    queryset = Event.objects.all()
    template_name = 'home/events/calendar.jinja'

    def get_list_queryset(self):
        tzinfo = tz.gettz(settings.TIME_ZONE)
        start = datetime_parse(self.request.query_params['start'])
        start = start.replace(tzinfo=tzinfo)
        end = datetime_parse(self.request.query_params['end'])
        end = end.replace(tzinfo=tzinfo)

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


class JobViewSet(viewsets.ModelViewSet):
    serializer_class = JobSerializer
    pagination_class = SmallResultSetPagination
    queryset = Job.objects.all()

    @property
    def template_name(self):
        return 'home/jobs/{}.jinja'.format(self.action)

    def get_queryset(self):
        return get_search_queryset(self)

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


class ProfileViewSet(viewsets.ModelViewSet):
    lookup_field = 'username'
    lookup_value_regex = '[\w\.\-@]+'
    serializer_class = UserSerializer
    queryset = User.objects.all()
    pagination_class = SmallResultSetPagination

    @property
    def template_name(self):
        return 'home/profiles/{}.jinja'.format(self.action)

    def get_queryset(self):
        # FIXME: this is broken, as Users / MemberProfiles do not have a `date_created` field
        # fix get_search_queryset to have a parameterizable ordering field
        return User.objects.filter(is_active=True)

    def retrieve(self, request, *args, **kwargs):
        return retrieve_with_perms(self, request, *args, **kwargs)


class FeaturedContentListAPIView(generics.ListAPIView):
    serializer_class = FeaturedContentItemSerializer
    queryset = FeaturedContentItem.objects.all()
    pagination_class = SmallResultSetPagination
