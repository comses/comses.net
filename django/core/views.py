import logging
from urllib import parse

import base64
import hashlib
import hmac
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db.models.functions import Lower
from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import DetailView, TemplateView
from itertools import chain
from rest_framework import filters, viewsets, generics
from rest_framework.exceptions import PermissionDenied as DrfPermissionDenied, NotAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .models import Event, Job
from .permissions import ComsesPermissions
from .serializers import EventSerializer, JobSerializer
from .utils import parse_datetime
from .view_helpers import get_search_queryset, retrieve_with_perms

logger = logging.getLogger(__name__)


class CaseInsensitiveOrderingFilter(filters.OrderingFilter):

    # a whitelist of acceptable ordering fields with ascending and descending forms (e.g., 'title', and '-title')
    STRING_ORDERING_FIELDS = list(chain.from_iterable([
        (f, '-' + f) for f in ('title', 'user__username', 'user__email', 'user__last_name',
                               'submitter__username', 'submitter__last_name', 'submitter__email',)
    ]))

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        if ordering:
            case_insensitive_ordering = []
            for field in ordering:
                if field not in self.STRING_ORDERING_FIELDS:
                    case_insensitive_ordering.append(field)
                elif field.startswith('-'):
                    case_insensitive_ordering.append(Lower(field[1:]).desc())
                else:
                    case_insensitive_ordering.append(Lower(field).asc())
            queryset = queryset.order_by(*case_insensitive_ordering)

        return queryset


def _common_namespace_path(model):
    meta = model._meta
    app_label = meta.app_label
    return '{0}/{1}'.format(app_label, meta.verbose_name_plural.replace(' ', '_'))


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

    ALLOWED_ACTIONS = ('list', 'retrieve', 'delete')
    namespace = None
    ext = 'jinja'

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
                # `django/<app-name>/templates/<namespace>/<action>.<file_ext>`.
                ts[action] = ['{0}/{1}.{2}'.format(namespace, action, file_ext)]
        if self.action in ts:
            return ts[self.action]
        logger.warning("Unhandled action %s, we only support list / retrieve / delete. Returning list template",
                       self.action)
        return ts['list']


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
        return ['{0}/{1}'.format(namespace, 'edit.jinja')]

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
        return super().dispatch(request, *args, **kwargs)


class FormUpdateView(PermissionRequiredByHttpMethodMixin, DetailView):
    method = 'PUT'


class FormCreateView(PermissionRequiredByHttpMethodMixin, TemplateView):
    method = 'POST'


def rest_exception_handler(exc, context):
    request = context.get('request')
    logger.warning("DRF exception handler %s", exc, exc_info=True)
    if request and request.accepted_media_type == 'text/html':
        if isinstance(exc, Http404):
            return page_not_found(request, context=context)
        elif isinstance(exc, (PermissionDenied, DrfPermissionDenied, NotAuthenticated)):
            return permission_denied(request, context=context)
        else:
            return server_error(request, context=context)
    else:
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


class SmallResultSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 200

    @staticmethod
    def _to_search_terms(query_params):
        return [v if k == 'query' else '{0}: {1}'.format(k, v) for k, v in query_params.items()]

    def get_paginated_response(self, data):
        query_params = self.request.query_params.copy()
        page = query_params.pop('page', [1])[0]
        count = self.page.paginator.count
        num_results = len(self.page.object_list)
        num_pages, remainder = divmod(count, self.page_size)
        if remainder > 0:
            num_pages += 1
        try:
            current_page_number = int(page)
        except:
            current_page_number = 1
        page_range = list(range(max(2, current_page_number - 3), min(num_pages, current_page_number + 4)))
        return Response({
            'is_first_page': current_page_number == 1,
            'is_last_page': current_page_number == num_pages,
            'current_page': current_page_number,
            'num_results': num_results,
            'count': count,
            'query': query_params.get('query'),
            'search_terms': self._to_search_terms(query_params),
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


class EventFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if view.action != 'list':
            return queryset

        qs = request.query_params.get('query')
        submission_deadline__gte = request.query_params.get('submission_deadline__gte')
        start_date__gte = parse_datetime(request.query_params.get('state_date__gte'))
        tags = request.query_params.getlist('tags')

        criteria = {}

        if submission_deadline__gte:
            criteria.update(submission_deadline__gte=submission_deadline__gte)
        if start_date__gte:
            criteria.update(start_date__gte=start_date__gte)
        return get_search_queryset(qs, queryset, tags=tags, criteria=criteria)


class EventViewSet(CommonViewSetMixin, viewsets.ModelViewSet):
    serializer_class = EventSerializer
    queryset = Event.objects.order_by('-date_created', 'title')
    pagination_class = SmallResultSetPagination
    filter_backends = (CaseInsensitiveOrderingFilter, EventFilter)
    ordering_fields = ('date_created', 'last_modified', 'title',
                       'submitter__last_name', 'submitter__username',)

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
        return self.queryset.find_by_interval(start, end), start, end

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

            if event.start_date:
                min_date = max(start, event.start_date)
                if event.end_date is None:
                    event.end_date = event.start_date
                max_date = min(end, event.end_date)
                if min_date <= max_date:
                    calendar_events.append(self.to_calendar_event(event))

        return Response(data=calendar_events)


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
    queryset = Job.objects.order_by('-date_created')
    filter_backends = (CaseInsensitiveOrderingFilter, JobFilter)
    ordering_fields = ('date_created', 'last_modified', 'title',
                       'submitter__last_name', 'submitter__username',)

    def get_queryset(self):
        return self.queryset

    def retrieve(self, request, *args, **kwargs):
        return retrieve_with_perms(self, request, *args, **kwargs)
