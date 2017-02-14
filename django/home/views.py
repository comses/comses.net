from library.models import Codebase, CodebaseRelease
from .models import Event, Job
from .serializers import EventSerializer, JobSerializer, TagSerializer
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.auth.models import User
from rest_framework import generics, viewsets
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.pagination import PageNumberPagination
from wagtail.wagtailsearch.models import Query
from django.shortcuts import render
from wagtail.wagtailsearch.backends import get_search_backend
import logging
from taggit.models import Tag

logger = logging.getLogger(__name__)

search = get_search_backend()


class SmallResultSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 200

    def get_paginated_response(self, data, **kwargs):
        count = self.page.paginator.count
        n_pages = count // self.page_size + 1
        page = int(self.request.query_params.get('page', 1))
        logger.debug("Request page")
        return Response({
            'page': page,
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
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer,)

    @property
    def template_name(self):
        return 'home/events/{}.jinja'.format(self.action)


class JobViewSet(viewsets.ModelViewSet):
    serializer_class = JobSerializer
    queryset = Job.objects.all()
    pagination_class = SmallResultSetPagination
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer,)

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

    def retrieve(self, request, *args, **kwargs):
        job = Job.objects.get(id=kwargs['pk'])
        serializer = JobSerializer(job)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        tag_names = [raw_tag['name'] for raw_tag in request.data['tags']]
        job = Job.objects.get(id=request.data['id'])
        logger.debug(tag_names)
        if job:
            job.tags.clear()
            job.tags.add(*tag_names)
            job.title = request.data['title']
            job.description = request.data['description']
            job.save()
        serializer = JobSerializer(job)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        submitter = request.user
        tags = request.data['tags']
        job = Job.objects.create(title=request.data['title'],
                                 description=request.data['description'],
                                 submitter=submitter)
        job.tags.add(*[tag['name'] for tag in tags])
        serializer = JobSerializer(job)
        return Response(serializer.data)


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    queryset = Tag.objects.all()
    pagination_class = SmallResultSetPagination
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer,)

    @property
    def template_name(self):
        return '/home/tags/{}.jinja'.format(self.action)

    def get_list_queryset(self):
        search_query = self.request.query_params.get('query')
        if search_query:
            queryset = Tag.objects.filter(name__icontains=search_query).order_by('name')
        else:
            queryset = Tag.objects.order_by('name')
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_list_queryset()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = TagSerializer(page, many=True)
            return self.get_paginated_response(data=serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
