from rest_framework import viewsets
from django.urls import resolve

from home.views import SmallResultSetPagination
from .models import Codebase, CodebaseRelease
from .serializers import CodebaseSerializer, CodebaseReleaseSerializer

import logging

logger = logging.getLogger(__name__)


class CodebaseViewSet(viewsets.ModelViewSet):
    lookup_field = 'identifier'
    lookup_value_regex = r'\w+'

    queryset = Codebase.objects.all()
    serializer_class = CodebaseSerializer
    pagination_class = SmallResultSetPagination

    @property
    def template_name(self):
        return 'library/codebase/{}.jinja'.format(self.action)


class CodebaseReleaseViewSet(viewsets.ModelViewSet):
    lookup_field = 'version_number'
    lookup_value_regex = r'\d+\.\d+\.\d+'

    queryset = CodebaseRelease.objects.all()
    serializer_class = CodebaseReleaseSerializer
    pagination_class = SmallResultSetPagination

    def get_queryset(self):
        resolved = resolve(self.request.path)
        identifier = resolved.kwargs['identifier']
        return self.queryset.filter(codebase__identifier=identifier)
