from .models import Event, Job
from .serializers import EventSerializer, JobSerializer, TagSerializer
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework import viewsets
from wagtail.wagtailsearch.backends import get_search_backend
import logging
from taggit.models import Tag

from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)

search = get_search_backend()


class SmallResultSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 200

    def get_paginated_response(self, data, **kwargs):
        count = self.page.paginator.count
        n_pages = count // self.page_size + 1
        page = int(self.request.query_params.get('page', 1))
        logger.debug("Request page")
        return Response({
            'current_page': page,
            'count': count,
            'query': self.request.query_params.get('query'),
            'range': list(range(max(1, page - 4), min(n_pages + 1, page + 5))),
            'n_pages': n_pages,
            'results': data
        }, **kwargs)


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    queryset = Event.objects.all()
    pagination_class = SmallResultSetPagination

    @property
    def template_name(self):
        return 'home/events/{}.jinja'.format(self.action)


class JobViewSet(viewsets.ModelViewSet):
    serializer_class = JobSerializer
    pagination_class = SmallResultSetPagination
    queryset = Job.objects.all()

    @property
    def template_name(self):
        return 'home/jobs/{}.jinja'.format(self.action)

    def get_list_queryset(self):
        search_query = self.request.query_params.get('query')
        if search_query:
            queryset = search.search(search_query, Job.objects.order_by('-date_created'))
        else:
            queryset = Job.objects.order_by('-date_created')
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_list_queryset()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = JobSerializer(page, many=True)
            return self.get_paginated_response(data=serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    class Meta:
        permissions = (('view_job', 'View Jobs'))


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    queryset = Tag.objects.all()
    pagination_class = SmallResultSetPagination

    @property
    def template_name(self):
        return '/home/tags/{}.jinja'.format(self.action)

    def get_list_queryset(self):
        search_query = self.request.query_params.get('query')
        if search_query:
            queryset = Tag.objects.filter(name__icontains=search_query).order_by('-date_created', 'name')
        else:
            queryset = Tag.objects.order_by('-date_created', 'name')
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_list_queryset()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = TagSerializer(page, many=True)
            return self.get_paginated_response(data=serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    class Meta:
        permissions = (('view_tag', 'View Tags'))