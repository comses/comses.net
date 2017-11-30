import base64
import hashlib
import hmac
import logging
from urllib import parse

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.files.images import ImageFile
from django.db.models.query_utils import Q
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework import viewsets, generics, parsers, status, mixins, filters, renderers
from rest_framework.decorators import detail_route, list_route
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from taggit.models import Tag
from wagtail.wagtailimages.models import Image
from wagtail.wagtailsearch.backends import get_search_backend

from core.models import FollowUser, Event, Job
from core.utils import parse_datetime
from core.view_helpers import get_search_queryset, retrieve_with_perms
from core.views import FormViewSetMixin, FormCreateView, FormUpdateView
from .common_serializers import RelatedMemberProfileSerializer
from .models import FeaturedContentItem, MemberProfile
from .serializers import (EventSerializer, JobSerializer, TagSerializer, FeaturedContentItemSerializer,
                          MemberProfileSerializer, UserMessageSerializer)

logger = logging.getLogger(__name__)

search = get_search_backend()


class SmallResultSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 200

    def get_paginated_response(self, data):
        query_params = self.request.query_params.copy()
        page = query_params.pop('page', [1])[0]
        count = self.page.paginator.count
        num_pages = count // self.page_size + 1

        try:
            current_page_number = int(page)
        except:
            current_page_number = 1
        page_range = list(range(max(2, current_page_number - 3), min(num_pages, current_page_number + 4)))
        return Response({
            'is_first_page': current_page_number == 1,
            'is_last_page': current_page_number == num_pages,
            'current_page': current_page_number,
            'page_size': self.page_size,
            'count': count,
            'query': query_params.get('query'),
            'query_params': query_params.urlencode(),
            'range': page_range,
            'num_pages': num_pages,
            'results': data
        })


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
    # See https://meta.discourse.org/t/official-single-sign-on-for-discourse-sso/13045
    # for full description of params that can be added
    params = {
        'nonce': qs['nonce'][0],
        'email': user.email,
        'external_id': user.id,
        'username': user.username,
        'require_activation': 'false',
        'name': user.get_full_name(),
    }
    # add an avatar_url to the params if the user has one
    avatar_url = user.member_profile.avatar_url
    if avatar_url:
        params.update(avatar_url=request.build_absolute_uri(avatar_url))

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
        start_date__gte = parse_datetime(request.query_params.get('state_date__gte'))
        tags = request.query_params.get('tags', [])

        if submission_deadline__gte:
            queryset = queryset.filter(submission_deadline__gte=submission_deadline__gte)
        if start_date__gte:
            queryset = queryset.filter(start_date__gte=start_date__gte)
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
            return queryset.filter(Q(user__username__istartswith=query) |
                                   Q(user__last_name__istartswith=query) |
                                   Q(user__first_name__istartswith=query) |
                                   Q(user__contributor__given_name__istartswith=query) |
                                   Q(user__contributor__family_name__istartswith=query))
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
        queryset = User.objects.filter(member_profile__in=self.get_queryset()).order_by('last_name')
        page = self.paginate_queryset(queryset)
        serializer = RelatedMemberProfileSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


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
