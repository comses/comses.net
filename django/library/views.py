from django.shortcuts import get_object_or_404
from rest_framework import viewsets

from home.views import SmallResultSetPagination
from .models import Codebase, CodebaseRelease
from .serializers import CodebaseSerializer, CodebaseReleaseSerializer

import logging

logger = logging.getLogger(__name__)


class CodebaseViewSet(viewsets.ModelViewSet):
    lookup_field = 'identifier'
    multiple_lookup_fields = ('identifier', 'uuid', 'pk')
    lookup_value_regex = '\w+'
    queryset = Codebase.objects.all()
    serializer_class = CodebaseSerializer
    pagination_class = SmallResultSetPagination

    def get_object(self):
        queryset = self.get_queryset()
        filter_dict = {}
        for field in self.multiple_lookup_fields:
            filter_value = self.kwargs.get(field)
            if filter_value:
                filter_dict[field] = filter_value
        obj = get_object_or_404(queryset, **filter_dict)
        self.check_object_permissions(self.request, obj)
        return obj


    @property
    def template_name(self):
        return 'library/codebase/{}.jinja'.format(self.action)


class CodebaseReleaseViewSet(viewsets.ModelViewSet):
    queryset = CodebaseRelease.objects.all()
    serializer_class = CodebaseReleaseSerializer
