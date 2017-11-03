import logging
import os

import pathlib
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import resolve
from django.views import View
from rest_framework import viewsets, generics, parsers, renderers, status, permissions, filters, mixins
from rest_framework.decorators import detail_route
from rest_framework.exceptions import PermissionDenied as DrfPermissionDenied, ValidationError
from rest_framework.response import Response

from core.permissions import ComsesPermissions
from core.view_helpers import add_change_delete_perms, get_search_queryset
from core.views import FormViewSetMixin, FormUpdateView, FormCreateView
from home.views import SmallResultSetPagination
from library.fs import CodebaseReleaseFsApi, PossibleDirectories, CodebaseReleaseFsApiWithActivityLog
from library.permissions import CodebaseReleaseUnpublishedFilePermissions
from .models import Codebase, CodebaseRelease, Contributor
from .serializers import (CodebaseSerializer, RelatedCodebaseSerializer, CodebaseReleaseSerializer,
                          ContributorSerializer, ReleaseContributorSerializer, CodebaseReleaseEditSerializer)

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

    def perform_create(self, serializer):
        codebase = serializer.save()
        release = codebase.get_or_create_draft()

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


class NestedCodebaseReleaseUnpublishedFilesPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.live:
            raise DrfPermissionDenied('Cannot access unpublished files of published release')
        if request.method == 'GET' and not request.user.has_perm('library.change_codebaserelease', obj=obj):
            raise DrfPermissionDenied('Must have change permission to view release')
        return True


class CodebaseReleaseViewSet(FormViewSetMixin, viewsets.ModelViewSet):
    namespace = 'library/codebases/releases/'
    lookup_field = 'version_number'
    lookup_value_regex = r'\d+\.\d+\.\d+'

    queryset = CodebaseRelease.objects.all()
    pagination_class = SmallResultSetPagination
    permission_classes = (NestedCodebaseReleasePermission, ComsesPermissions,)

    def get_serializer_class(self):
        edit = self.request.query_params.get('edit')
        if edit is not None:
            return CodebaseReleaseEditSerializer
        else:
            return CodebaseReleaseSerializer

    @property
    def template_name(self):
        return 'library/codebases/releases/{}.jinja'.format(self.action)

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

    def get_queryset(self):
        resolved = resolve(self.request.path)
        identifier = resolved.kwargs['identifier']
        queryset = self.queryset.filter(codebase__identifier=identifier)
        if self.action == 'list':
            return queryset.public()
        else:
            return queryset.accessible(user=self.request.user)

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

    @detail_route(methods=['get'])
    def download(self, request, **kwargs):
        codebase_release = self.get_object()
        response = FileResponse(codebase_release.retrieve_archive())
        response['Content-Disposition'] = 'attachment; filename={}'.format(
            '{}_v{}.zip'.format(codebase_release.codebase.title.lower().replace(' ', '_'),
                                codebase_release.version_number))
        return response


class CodebaseReleaseUnpublishedFilesViewSet(viewsets.GenericViewSet):
    lookup_field = 'relpath'
    lookup_value_regex = r'.*'

    queryset = CodebaseRelease.objects.all()
    pagination_class = SmallResultSetPagination
    permission_classes = (NestedCodebaseReleaseUnpublishedFilesPermission, CodebaseReleaseUnpublishedFilePermissions,)
    renderer_classes = (renderers.JSONRenderer,)

    def get_queryset(self):
        resolved = resolve(self.request.path)
        identifier = resolved.kwargs['identifier']
        queryset = self.queryset.filter(codebase__identifier=identifier)
        return queryset.accessible(user=self.request.user)

    def get_folder(self) -> PossibleDirectories:
        foldername = self.get_parser_context(self.request)['kwargs']['foldername']
        try:
            return PossibleDirectories[foldername]
        except KeyError:
            raise ValidationError('Target folder name {} invalid. Must be one of {}'.format(foldername, list(
                d.name for d in PossibleDirectories)))

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())

        parser_context = self.get_parser_context(self.request)
        kwargs = parser_context['kwargs']
        identifier = kwargs['identifier']
        version_number = kwargs['version_number']
        obj = get_object_or_404(queryset, codebase__identifier=identifier,
                                version_number=version_number)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def list(self, request, identifier, version_number, foldername, **kwargs):
        codebase_release = self.get_object()
        api = CodebaseReleaseFsApi(codebase_release)
        folder = self.get_folder()
        return Response(data={
            'files': list(api.list(folder)),
            'upload_url': api.get_list_url(folder=folder)}, status=status.HTTP_200_OK)

    def create(self, request, identifier, version_number, foldername, **kwargs):
        codebase_release = self.get_object()
        dest_folder = self.get_folder()
        fileobj = request.data.get('file')
        if fileobj is None:
            raise ValidationError({'file': ['This field is required']})
        with CodebaseReleaseFsApiWithActivityLog(codebase_release) as api:
            api.add(fileobj=fileobj, dest_folder=dest_folder)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, *args, **kwargs):
        relpath = kwargs['relpath']
        codebase_release = self.get_object()
        folder = self.get_folder()
        with CodebaseReleaseFsApiWithActivityLog(codebase_release) as api:
            api.delete(folder, pathlib.Path(relpath))
        return Response(status=status.HTTP_202_ACCEPTED)


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


class ContributorFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        q = request.query_params.get('query')
        queryset = get_search_queryset(q, queryset)
        return queryset


class ContributorList(generics.ListAPIView):
    queryset = Contributor.objects.all()
    serializer_class = ContributorSerializer
    pagination_class = SmallResultSetPagination
    filter_backends = (ContributorFilter,)
