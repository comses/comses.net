from .models import Event, Job, Model, ModelVersion
from .serializers import EventSerializer, JobSerializer, ModelSerializer, ModelVersionSerializer
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from rest_framework import generics, viewsets
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.pagination import PageNumberPagination
from wagtail.wagtailsearch.models import Query
from django.shortcuts import render
from wagtail.wagtailsearch.backends import get_search_backend

search = get_search_backend()


class SmallResultSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 200

    def get_paginated_response(self, data, **kwargs):
        count = self.page.paginator.count
        n_pages = count // self.page_size + 1
        page_ind = int(self.request.query_params.get('page', 1))
        return Response({
            'page_ind': page_ind,
            'count': count,
            'query': self.request.query_params.get('query'),
            'range': list(range(max(1, page_ind - 4), min(n_pages + 1, page_ind + 5))),
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
        return 'home/event/{}.html'.format(self.action)


class JobViewSet(viewsets.ModelViewSet):
    serializer_class = JobSerializer
    queryset = Job.objects.all()
    pagination_class = SmallResultSetPagination
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer,)

    @property
    def template_name(self):
        return 'home/job/{}.html'.format(self.action)

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


class ModelViewSet(viewsets.ModelViewSet):
    queryset = Model.objects.all()
    serializer_class = ModelSerializer
    pagination_class = SmallResultSetPagination
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer,)

    @property
    def template_name(self):
        return 'home/model/{}.html'.format(self.action)
