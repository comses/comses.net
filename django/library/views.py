import logging
import os

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import resolve
from django.views import View
from rest_framework import viewsets, generics, parsers, renderers, status, permissions
from rest_framework.decorators import detail_route
from rest_framework.exceptions import PermissionDenied as DrfPermissionDenied
from rest_framework.response import Response

from core.permissions import ComsesPermissions
from core.view_helpers import add_change_delete_perms
from core.views import FormViewSetMixin, FormUpdateView, FormCreateView
from home.views import SmallResultSetPagination
from .models import Codebase, CodebaseRelease, Contributor
from .serializers import (CodebaseSerializer, RelatedCodebaseSerializer, CodebaseReleaseSerializer,
                          ContributorSerializer, ReleaseContributorSerializer)

logger = logging.getLogger(__name__)


def has_permission_to_create_release(request, view, exception_class):
    user = request.user
    codebase = get_object_or_404(Codebase, identifier=view.kwargs['identifier'])
    if request.method == 'POST':
        required_perms = ['library.change_codebase']
    else:
        required_perms = []

    if user.has_perms(required_perms, obj=codebase):
        return True
    raise exception_class


class CodebaseViewSet(FormViewSetMixin, viewsets.ModelViewSet):
    lookup_field = 'identifier'
    lookup_value_regex = r'[\w\-\.]+'
    pagination_class = SmallResultSetPagination
    queryset = Codebase.objects.all()

    # FIXME: should we use filter_backends
    # (http://www.django-rest-framework.org/api-guide/filtering/#djangoobjectpermissionsfilter)
    # instead of get_search_queryset?
    # filter_backends = (filters.DjangoObjectPermissionsFilter,)

    def get_queryset(self):
        if self.action == 'list':
            return self.queryset.public()
        else:
            # On detail pages we want to see unpublished releases
            return self.queryset.accessible(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'list':
            return RelatedCodebaseSerializer
        return CodebaseSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        # check content negotiation to see if we should redirect to the latest release detail page or if this is an API
        # request for a JSON serialization of this Codebase.
        # FIXME: this should go away if/when we segregate DRF API calls under /api/v1/codebases/
        if request.accepted_media_type == 'text/html':
            current_version = instance.latest_version
            if not current_version:
                raise Http404
            return redirect(current_version)
        else:
            serializer = self.get_serializer(instance)
            data = add_change_delete_perms(instance, serializer.data, request.user)
            return Response(data)


class CodebaseReleaseDraftView(PermissionRequiredMixin, View):
    def has_permission(self):
        return has_permission_to_create_release(view=self, request=self.request, exception_class=PermissionDenied)

    def post(self, *args, **kwargs):
        identifier = kwargs['identifier']
        codebase = get_object_or_404(Codebase, identifier=kwargs['identifier'])
        codebase_release = codebase.releases.filter(draft=True).first()
        if not codebase_release:
            codebase_release = codebase.create_release()
        version_number = codebase_release.version_number
        return redirect('library:codebaserelease-edit', identifier=identifier, version_number=version_number)


class CodebaseFormCreateView(FormCreateView):
    model = Codebase


class CodebaseFormUpdateView(FormUpdateView):
    model = Codebase
    slug_field = 'identifier'
    slug_url_kwarg = 'identifier'


class NestedCodebaseReleasePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return has_permission_to_create_release(request=request, view=view, exception_class=DrfPermissionDenied)


class CodebaseReleaseViewSet(FormViewSetMixin, viewsets.ModelViewSet):
    namespace = 'library/codebases/releases/'
    lookup_field = 'version_number'
    lookup_value_regex = r'\d+\.\d+\.\d+'

    queryset = CodebaseRelease.objects.all()
    serializer_class = CodebaseReleaseSerializer
    pagination_class = SmallResultSetPagination
    permission_classes = (NestedCodebaseReleasePermission, ComsesPermissions,)

    @property
    def template_name(self):
        return 'library/codebases/releases/{}.jinja'.format(self.action)

    def get_queryset(self):
        resolved = resolve(self.request.path)
        identifier = resolved.kwargs['identifier']
        queryset = self.queryset.filter(codebase__identifier=identifier)
        if self.action == 'list':
            return queryset.public()
        else:
            return queryset.accessible(user=self.request.user)

    def _list_uploads(self, codebase_release, upload_type, url):
        return Response(data={
            'files': codebase_release.list_uploads(upload_type),
            'upload_url': url}, status=200)

    def _file_upload_operations(self, request, upload_type: str, url):
        codebase_release = self.get_object()  # type: CodebaseRelease
        if request.method == 'POST':
            if codebase_release.live:
                raise DrfPermissionDenied(detail='files cannot be added on published releases')
            codebase_release.add_upload(upload_type, request.data['file'])
            return Response(status=204)
        elif request.method == 'GET':
            return self._list_uploads(codebase_release, upload_type, url)

    def create(self, request, *args, **kwargs):
        identifier = kwargs['identifier']
        codebase = get_object_or_404(Codebase, identifier=identifier)
        codebase_release = codebase.get_or_create_draft()
        codebase_release_serializer = self.get_serializer_class()
        serializer = codebase_release_serializer(codebase_release)
        headers = self.get_success_headers(serializer.data)
        return Response(status=status.HTTP_201_CREATED, data=serializer.data, headers=headers)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = add_change_delete_perms(instance, serializer.data, request.user)
        return Response(data)

    @detail_route(methods=['get'],
                  renderer_classes=(renderers.JSONRenderer,))
    def download(self, request, **kwargs):
        codebase_release = self.get_object()
        response = FileResponse(codebase_release.retrieve_archive())
        response['Content-Disposition'] = 'attachment; filename={}'.format(
            '{}_v{}.zip'.format(codebase_release.codebase.title.lower().replace(' ', '_'),
                                codebase_release.version_number))
        return response

    @detail_route(methods=['get', 'post'],
                  parser_classes=(parsers.FormParser, parsers.MultiPartParser,),
                  renderer_classes=(renderers.JSONRenderer,),
                  url_name='files',
                  url_path='files/(?P<upload_type>[\.\w]+)')
    def files(self, request, identifier, version_number, upload_type):
        url = request.path
        return self._file_upload_operations(request, upload_type, url)

    @detail_route(methods=['delete', 'get'],
                  parser_classes=(parsers.JSONParser,),
                  url_name='download_unpublished',
                  url_path='files/(?P<upload_type>[\.\w]+)/(?P<path>([\.\w ]+/)*[\.\w\- ]+)')
    def download_unpublished(self, request, identifier, version_number, upload_type, path):
        codebase_release = self.get_object()
        if request.method == 'DELETE':
            if codebase_release.live:
                raise DrfPermissionDenied(detail='files cannot be deleted from published releases')
            codebase_release.delete_upload(upload_type, path)
            return self._list_uploads(codebase_release, upload_type, request.path)
        elif request.method == 'GET':
            filename = os.path.basename(path)
            response = FileResponse(codebase_release.retrieve_upload(upload_type, path))
            response['Content-Disposition'] = 'attachment; filename={}'.format(filename)
            return response

    @detail_route(methods=['put'])
    def contributors(self, request, **kwargs):
        codebase_release = self.get_object()
        crs = ReleaseContributorSerializer(many=True, data=request.data, context={'release_id': codebase_release.id},
                                           allow_empty=False)
        crs.is_valid(raise_exception=True)
        crs.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @detail_route(methods=['post'])
    def publish(self, request, **kwargs):
        codebase_release = self.get_object()
        codebase_release.publish()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CodebaseReleaseFormCreateView(FormCreateView):
    namespace = 'codebases/releases'
    model = CodebaseRelease


class CodebaseReleaseFormUpdateView(FormUpdateView):
    namespace = 'codebases/releases'
    model = CodebaseRelease

    def get_object(self, queryset=None):
        identifier = self.kwargs['identifier']
        version_number = self.kwargs['version_number']
        return get_object_or_404(queryset or CodebaseRelease,
                                 version_number=version_number,
                                 codebase__identifier=identifier)


class ContributorList(generics.ListAPIView):
    queryset = Contributor.objects.all()
    serializer_class = ContributorSerializer
    pagination_class = SmallResultSetPagination

    def get_queryset(self):
        q = {'given_name__istartswith': self.request.query_params.get('given_name'),
             'family_name__istartswith': self.request.query_params.get('family_name'),
             'type': self.request.query_params.get('type')}
        q = {k: v for k, v in q.items() if v}
        return self.queryset.filter(**q).order_by('family_name')
