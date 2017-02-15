from .serializers import CodebaseSerializer, CodebaseReleaseSerializer
from rest_framework.pagination import PageNumberPagination
from rest_framework import viewsets

from .models import Codebase, CodebaseRelease


class CodebaseViewSet(viewsets.ModelViewSet):
    queryset = Codebase.objects.all()
    serializer_class = CodebaseSerializer
    pagination_class = PageNumberPagination

    @property
    def template_name(self):
        return 'home/model/{}.html'.format(self.action)


class CodebaseReleaseViewSet(viewsets.ModelViewSet):
    queryset = CodebaseRelease.objects.all()
    serializer_class = CodebaseReleaseSerializer
