from .serializers import CodebaseSerializer, CodebaseReleaseSerializer
from home.views import SmallResultSetPagination
from rest_framework import viewsets
from core.backends import get_viewable_objects_for_user
from django.contrib.auth.models import User
from django.conf import settings

from .models import Codebase, CodebaseRelease
from core.view_helpers import get_search_queryset


class CodebaseViewSet(viewsets.ModelViewSet):
    queryset = Codebase.objects.all()
    serializer_class = CodebaseSerializer
    pagination_class = SmallResultSetPagination

    def get_queryset(self):
        return get_search_queryset(self)

    @property
    def template_name(self):
        return 'library/codebase/{}.jinja'.format(self.action)


class CodebaseReleaseViewSet(viewsets.ModelViewSet):
    queryset = CodebaseRelease.objects.all()
    serializer_class = CodebaseReleaseSerializer
