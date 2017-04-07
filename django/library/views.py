from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from django.urls import resolve

from home.views import SmallResultSetPagination
from .models import Codebase, CodebaseRelease
from .serializers import CodebaseSerializer, CodebaseReleaseSerializer

import logging

logger = logging.getLogger(__name__)


class CodebaseViewSet(viewsets.ModelViewSet):
    lookup_field = 'identifier'
    lookup_url_kwarg = 'pk'
    lookup_value_regex = '\w+'

    queryset = Codebase.objects.all()
    serializer_class = CodebaseSerializer
    pagination_class = SmallResultSetPagination

    @property
    def template_name(self):
        return 'library/codebase/{}.jinja'.format(self.action)


class CodebaseReleaseViewSet(viewsets.ModelViewSet):
    lookup_field = 'id'
    lookup_url_kwarg = 'release_pk'

    queryset = CodebaseRelease.objects.all()
    serializer_class = CodebaseReleaseSerializer

    def get_queryset(self):
        resolved = resolve(self.request.path)
        codebase_id = resolved.kwargs['pk']
        return self.queryset.filter(codebase_id=codebase_id)