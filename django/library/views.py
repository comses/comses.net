import logging

from django.urls import resolve
from rest_framework import viewsets

from core.view_helpers import get_search_queryset
from home.views import SmallResultSetPagination
from .models import Codebase, CodebaseRelease
from .serializers import CodebaseSerializer, CodebaseReleaseSerializer

logger = logging.getLogger(__name__)


class CodebaseViewSet(viewsets.ModelViewSet):
    lookup_field = 'identifier'
    lookup_value_regex = r'[\w\-.]+'
    serializer_class = CodebaseSerializer
    pagination_class = SmallResultSetPagination
    queryset = Codebase.objects.all()

    def get_queryset(self):
        return get_search_queryset(self)

    @property
    def template_name(self):
        return 'library/codebases/{}.jinja'.format(self.action)


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
