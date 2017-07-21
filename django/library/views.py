import logging

from django.core.files import File
from django.urls import resolve
from rest_framework import viewsets, generics, parsers, renderers
from rest_framework.decorators import detail_route
from rest_framework.response import Response

from core.view_helpers import get_search_queryset, add_change_delete_perms
from home.views import SmallResultSetPagination
from .models import Codebase, CodebaseRelease, Contributor
from .serializers import (CodebaseSerializer, RelatedCodebaseSerializer, CodebaseReleaseSerializer,
                          ContributorSerializer, )

logger = logging.getLogger(__name__)


class CodebaseViewSet(viewsets.ModelViewSet):
    lookup_field = 'identifier'
    lookup_value_regex = r'[\w\-.]+'
    pagination_class = SmallResultSetPagination
    queryset = Codebase.objects.all()

    def get_queryset(self):
        return get_search_queryset(self)

    def get_serializer_class(self):
        if self.action == 'list':
            return RelatedCodebaseSerializer
        return CodebaseSerializer

    @property
    def template_name(self):
        return 'library/codebases/{}.jinja'.format(self.action)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if 'version_number' in kwargs:
            instance.current_version = instance.releases.get(version_number=kwargs['version_number'])
        else:
            instance.current_version = instance.latest_version
        serializer = self.get_serializer(instance)
        data = add_change_delete_perms(instance, serializer.data, request.user)
        return Response(data)


class CodebaseReleaseViewSet(viewsets.ModelViewSet):
    lookup_field = 'version_number'
    lookup_value_regex = r'\d+\.\d+\.\d+'

    queryset = CodebaseRelease.objects.all()
    serializer_class = CodebaseReleaseSerializer
    pagination_class = SmallResultSetPagination

    @property
    def template_name(self):
        return 'library/codebases/releases/{}.jinja'.format(self.action)

    def get_queryset(self):
        resolved = resolve(self.request.path)
        identifier = resolved.kwargs['identifier']
        return self.queryset.filter(codebase__identifier=identifier)

    @detail_route(methods=['post'],
                  parser_classes=(parsers.FormParser, parsers.MultiPartParser,),
                  renderer_classes=(renderers.JSONRenderer,))
    def upload_data(self, request, identifier, version_number):
        codebase_release = self.get_object()  # type: CodebaseRelease
        codebase_release.add_data_upload(request.data['file'])
        return Response(status=204)

    @detail_route(methods=['post'],
                  parser_classes=(parsers.FormParser, parsers.MultiPartParser,),
                  renderer_classes=(renderers.JSONRenderer,))
    def upload_src(self, request, identifier, version_number):
        codebase_release = self.get_object()
        codebase_release.add_upload_src(request.data['file'])
        return Response(status=204)

    @detail_route(methods=['post'],
                  parser_classes=(parsers.FormParser, parsers.MultiPartParser,),
                  renderer_classes=(renderers.JSONRenderer,))
    def upload_doc(self, request, identifier, version_number):
        codebase_release = self.get_object()
        codebase_release.add_upload_doc(request.data['file'])
        return Response(status=204)

    @detail_route(methods=['post'],
                  parser_classes=(parsers.JSONParser,),
                  renderer_classes=(renderers.JSONRenderer,),
                  url_name='upload-delete',
                  url_path='upload_delete/(?P<path>[\.\w+/]*[\.\w]+)')
    def upload_delete(self, request, identifier, version_number, path):
        codebase_release = self.get_object()
        codebase_release.delete_upload(path)
        return Response(status=204)


class ContributorList(generics.ListAPIView):
    queryset = Contributor.objects.all()
    serializer_class = ContributorSerializer
    pagination_class = SmallResultSetPagination

    def get_queryset(self):
        q = {'given_name': self.request.query_params.get('given_name'),
             'family_name': self.request.query_params.get('family_name'),
             'type': self.request.query_params.get('type')}
        q = {k: v for k, v in q.items() if v}
        return self.queryset.filter(**q).order_by('family_name')


class CodebaseReleaseUploadView(generics.CreateAPIView):
    queryset = CodebaseRelease.objects.all()
    serializer_class = CodebaseReleaseSerializer
    parser_classes = (parsers.MultiPartParser, parsers.JSONParser,)
    renderer = renderers.JSONRenderer()

    def create(self, request, *args, **kwargs):
        file_obj = File(request.data['file'])
        codebase_identifier = kwargs.get('identifier')
        codebase = Codebase.objects.get(identifier=codebase_identifier)
        codebase_release = codebase.make_release(submitter=request.user, submitted_package=file_obj)
        data = CodebaseReleaseSerializer(instance=codebase_release).data
        return Response(data=data, status=200)
