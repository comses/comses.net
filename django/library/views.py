import logging
import pathlib

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import resolve
from django.views import View
from django.views.generic.base import RedirectView
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView
from django_jinja.views.generic import ListView
from rest_framework import viewsets, generics, renderers, status, permissions, filters, mixins
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied as DrfPermissionDenied, ValidationError
from rest_framework.response import Response

from core.models import MemberProfile
from core.permissions import ViewRestrictedObjectPermissions
from core.view_helpers import add_change_delete_perms, get_search_queryset
from core.views import (CommonViewSetMixin, FormUpdateView, FormCreateView, SmallResultSetPagination,
                        CaseInsensitiveOrderingFilter, NoDeleteViewSet,
                        NoDeleteNoUpdateViewSet, HtmlNoDeleteViewSet)
from .forms import (PeerReviewerFeedbackReviewerForm, PeerReviewInvitationReplyForm, PeerReviewInvitationForm,
                    PeerReviewerFeedbackEditorForm)
from .fs import FileCategoryDirectories, StagingDirectories, MessageLevels
from .models import (Codebase, CodebaseRelease, Contributor, CodebaseImage, PeerReview, PeerReviewerFeedback,
                     PeerReviewInvitation, ReviewStatus)
from .permissions import CodebaseReleaseUnpublishedFilePermissions
from .serializers import (CodebaseSerializer, CodebaseReleaseSerializer, ContributorSerializer,
                          ReleaseContributorSerializer, CodebaseReleaseEditSerializer, CodebaseImageSerializer,
                          PeerReviewInvitationSerializer, PeerReviewFeedbackEditorSerializer,
                          PeerReviewReviewerSerializer, PeerReviewEventLogSerializer)

logger = logging.getLogger(__name__)


def has_permission_to_create_release(request, view):
    user = request.user
    codebase = get_object_or_404(Codebase, identifier=view.kwargs['identifier'])
    if request.method == 'POST':
        required_perms = ['library.change_codebase']
    else:
        required_perms = []
    return user.has_perms(required_perms, obj=codebase)


class PeerReviewDashboardView(ListView):
    template_name = 'library/review/dashboard.jinja'
    model = PeerReview
    context_object_name = 'reviews'


class PeerReviewEditorView(PermissionRequiredMixin, DetailView):
    context_object_name = 'review'
    model = PeerReview
    permission_required = 'library.change_peerreview'
    slug_field = 'slug'
    template_name = 'library/review/editor_update.jinja'

    def put(self, request, *args, **kwargs):
        request.kwargs = kwargs
        return _change_peer_review_status(request)


class PeerReviewReviewerListView(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = MemberProfile.objects.all()
    serializer_class = PeerReviewReviewerSerializer

    def get_queryset(self):
        query = self.request.query_params.get('query', '')
        results = PeerReview.get_reviewers(query)
        return results


@api_view(['PUT'])
@permission_classes([])
def _change_peer_review_status(request):
    if not request.user.has_perm('library.change_peerreview'):
        raise PermissionDenied()
    slug = request.kwargs.get('slug')
    review = get_object_or_404(PeerReview, slug=slug)

    raw_status = request.data['status']
    try:
        new_status = ReviewStatus[raw_status]
    except KeyError:
        raise ValidationError('status {} not valid'.format(raw_status))
    review.editor_change_review_status(request.user.member_profile, new_status)

    return Response(data={'status': new_status.name}, status=status.HTTP_200_OK)


class NestedPeerReviewInvitation(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.has_perm('library.change_peerreview'):
            return True
        raise DrfPermissionDenied


class PeerReviewInvitationViewSet(NoDeleteNoUpdateViewSet):
    queryset = PeerReviewInvitation.objects.with_reviewer_statistics()
    permission_classes = (NestedPeerReviewInvitation,)
    renderer_classes = (renderers.JSONRenderer,)
    serializer_class = PeerReviewInvitationSerializer
    lookup_url_kwarg = 'invitation_slug'

    def get_queryset(self):
        slug = self.kwargs['slug']
        return self.queryset.filter(review__slug=slug)

    @transaction.atomic
    @action(detail=False, methods=['post'])
    def send_invitation(self, request, slug):
        data = request.data
        candidate_reviewer_id = data.get('id')
        candidate_email = data.get('email')
        form_data = dict(review=get_object_or_404(PeerReview, slug=slug).id,
                         editor=request.user.member_profile.id)
        if candidate_reviewer_id is not None:
            form_data['candidate_reviewer'] = candidate_reviewer_id
        elif candidate_email is not None:
            form_data['candidate_email'] = candidate_email
        else:
            raise ValidationError('Must have either id or email fields')
        form = PeerReviewInvitationForm(data=form_data)
        if form.is_valid():
            form.save()
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=form.errors)

    @transaction.atomic
    @action(detail=True, methods=['post'])
    def resend_invitation(self, request, slug, invitation_slug):
        invitation = get_object_or_404(PeerReviewInvitation, slug=invitation_slug)
        invitation.send_email()
        return Response(status=status.HTTP_200_OK)


class PeerReviewInvitationUpdateView(UpdateView):
    context_object_name = 'invitation'
    form_class = PeerReviewInvitationReplyForm
    queryset = PeerReviewInvitation.objects.all()
    template_name = 'library/review/invitations/update.jinja'

    def get_object(self, queryset=None):
        slug = self.kwargs['slug']
        invitation = get_object_or_404(PeerReviewInvitation, slug=slug)
        if invitation.accepted in [False, True]:
            raise PermissionDenied('Can only accept or decline invitation once')
        return invitation

    def get_success_url(self):
        if self.object.accepted:
            feedback = self.object.feedback_set.last()
            if feedback is None:
                feedback = self.object.create_feedback()
            return feedback.get_absolute_url()
        else:
            return self.object.review.codebase_release.share_url


class PeerReviewFeedbackViewSet(NoDeleteNoUpdateViewSet):
    queryset = PeerReviewerFeedback.objects.all()
    renderer_classes = (renderers.JSONRenderer,)
    serializer_class = PeerReviewFeedbackEditorSerializer

    def get_queryset(self):
        slug = self.kwargs['slug']
        return self.queryset.filter(invitation__review__slug=slug)


class PeerReviewFeedbackUpdateView(UpdateView):
    context_object_name = 'review_feedback'
    form_class = PeerReviewerFeedbackReviewerForm
    template_name = 'library/review/feedback/update.jinja'

    def get_context_data(self, **kwargs):
        feedback_set = PeerReviewerFeedback.objects \
            .filter(invitation__review=self.object.invitation.review) \
            .exclude(id=self.object.id)
        context = super().get_context_data(**kwargs)
        context['feedback_set'] = feedback_set
        return context

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = PeerReviewerFeedback.objects.all()
        feedback = get_object_or_404(queryset, invitation__slug=self.kwargs['slug'], id=self.kwargs['feedback_id'])
        if not feedback.invitation.accepted:
            raise PermissionDenied('Cannot access feedback of declined review')
        return feedback

    def get_success_url(self):
        if self.object.reviewer_submitted:
            return self.object.invitation.candidate_reviewer.get_absolute_url()
        else:
            return self.object.get_absolute_url()


class PeerReviewEditorFeedbackUpdateView(UpdateView):
    context_object_name = 'review_feedback'
    form_class = PeerReviewerFeedbackEditorForm
    template_name = 'library/review/feedback/editor_update.jinja'

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = PeerReviewerFeedback.objects.all()
        feedback = get_object_or_404(queryset, invitation__slug=self.kwargs['slug'], id=self.kwargs['feedback_id'])
        return feedback

    def get_success_url(self):
        return self.object.invitation.review.get_absolute_url()


@api_view(['get'])
@permission_classes([])
def list_review_event_log(request, slug):
    review = get_object_or_404(PeerReview, slug=slug)
    if not MemberProfile.objects.editors().filter(pk=request.user.member_profile.pk).exists():
        raise Http404()
    queryset = review.events.order_by('-date_created')[:10]
    serializer = PeerReviewEventLogSerializer(queryset, many=True)
    return Response(serializer.data)


class CodebaseFilter(filters.BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):
        if view.action != 'list':
            return queryset
        query_params = request.query_params
        qs = query_params.get('query')
        published_start_date = query_params.get('published_after')
        published_end_date = query_params.get('published_before')
        # platform = query_params.get('platform')
        # programming_language = query_params.get('programming_language')
        tags = query_params.getlist('tags')
        criteria = {}
        if published_start_date and published_end_date:
            if published_start_date < published_end_date:
                criteria.update(first_published_at__range=[published_start_date, published_end_date])
            else:
                logger.warning("invalid date range: %s, %s", published_start_date, published_end_date)
        elif published_start_date:
            criteria.update(first_published_at__gte=published_start_date)
        elif published_end_date:
            criteria.update(first_published_at__lte=published_end_date)
        return get_search_queryset(qs, queryset, tags=tags, criteria=criteria)


class CodebaseViewSet(CommonViewSetMixin,
                      HtmlNoDeleteViewSet):
    lookup_field = 'identifier'
    lookup_value_regex = r'[\w\-\.]+'
    pagination_class = SmallResultSetPagination
    queryset = Codebase.objects.with_tags().with_featured_images().order_by('-first_published_at', 'title')
    filter_backends = (CaseInsensitiveOrderingFilter, CodebaseFilter)
    permission_classes = (ViewRestrictedObjectPermissions,)
    serializer_class = CodebaseSerializer
    ordering_fields = ('first_published_at', 'title', 'last_modified', 'peer_reviewed', 'submitter__last_name',
                       'submitter__username')
    context_list_name = 'codebases'

    def get_queryset(self):
        if self.action == 'list':
            # On detail pages we want to see unpublished releases
            return self.queryset.public()
        else:
            return self.queryset.accessible(user=self.request.user)

    def perform_create(self, serializer):
        codebase = serializer.save()
        return codebase.get_or_create_draft()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # check content negotiation to see if we should redirect to the latest release detail page or if this is an API
        # request for a JSON serialization of this Codebase.
        # FIXME: this should go away if/when we segregate DRF API calls under /api/v1/codebases/
        if request.accepted_media_type == 'text/html':
            current_version = CodebaseRelease.objects.accessible(request.user).filter(codebase=instance).order_by(
                '-date_created').first()
            if not current_version:
                raise Http404
            return redirect(current_version)
        else:
            serializer = self.get_serializer(instance)
            data = add_change_delete_perms(instance, serializer.data, request.user)
            return Response(data)


class DevelopmentCodebaseDeleteView(mixins.DestroyModelMixin, CodebaseViewSet):
    lookup_field = 'identifier'
    lookup_value_regex = r'[\w\-\.]+'
    pagination_class = SmallResultSetPagination
    queryset = Codebase.objects.with_tags().with_featured_images().order_by('-first_published_at', 'title')
    filter_backends = (CaseInsensitiveOrderingFilter, CodebaseFilter)
    ordering_fields = ('first_published_at', 'title', 'last_modified', 'peer_reviewed', 'submitter__last_name',
                       'submitter__username')

    def get_queryset(self):
        if self.action == 'list':
            # On detail pages we want to see unpublished releases
            return self.queryset.public()
        else:
            return self.queryset.accessible(user=self.request.user)

    def perform_destroy(self, instance):
        instance.releases.all().delete()
        instance.delete()


class CodebaseVersionRedirectView(RedirectView):
    """
    Provides simple redirection from legacy openabm.org model library incremental version numbers (e.g., 1, 2, 3, 4, 5)
    to semver versioning where 1 -> 1.0.0, 2 -> 1.1.0, 3 -> 1.2.0 etc.
    """
    permanent = True
    pattern_name = 'library:codebaserelease-detail'

    def get_redirect_url(self, *args, **kwargs):
        simple_version_number = max(1, int(kwargs['version_number']))
        semver_number = '1.{0}.0'.format(simple_version_number - 1)
        kwargs.update(version_number=semver_number)
        return super().get_redirect_url(*args, **kwargs)


class CodebaseImagePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        codebase = get_object_or_404(Codebase, identifier=view.kwargs['identifier'])
        return request.user.has_perm('library.change_codebase', codebase)


class CodebaseImageViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    lookup_field = 'codebaseimage_id'
    lookup_value_regex = r'\d+'
    queryset = CodebaseImage.objects.all()
    serializer_class = CodebaseImageSerializer
    renderer_classes = (renderers.JSONRenderer,)
    permission_classes = (CodebaseImagePermission,)

    def get_queryset(self):
        resolved = resolve(self.request.path)
        identifier = resolved.kwargs['identifier']
        return self.queryset.filter(codebase__identifier=identifier)

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        parser_context = self.get_parser_context(self.request)
        kwargs = parser_context['kwargs']
        codebase_image_id = kwargs['codebaseimage_id']
        return get_object_or_404(queryset, id=codebase_image_id)

    def create(self, request, *args, **kwargs):
        codebase = get_object_or_404(Codebase, identifier=kwargs['identifier'])
        fileobj = request.data.get('file')
        if fileobj is None:
            raise ValidationError({'file': ['This field is required']})
        image = codebase.import_media(fileobj, user=request.user)
        if image is None:
            raise ValidationError([{'msg': {'detail': 'file is not an image', 'stage': 'media'}}])
        codebase.save()
        return Response(status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        codebaseimage = self.get_object()
        codebaseimage.file.storage.delete(codebaseimage.file.path)
        codebaseimage.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['delete'])
    def clear(self, request, *args, **kwargs):
        codebase = get_object_or_404(Codebase, identifier=kwargs['identifier'])
        for codebase_image in codebase.featured_images.all():
            codebase_image.file.storage.delete(codebase_image.file.path)
            codebase_image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CodebaseReleaseDraftView(PermissionRequiredMixin, View):
    def has_permission(self):
        if has_permission_to_create_release(view=self, request=self.request):
            return True
        raise PermissionDenied

    def post(self, *args, **kwargs):
        identifier = kwargs['identifier']
        codebase = get_object_or_404(Codebase, identifier=identifier)
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
        if has_permission_to_create_release(request=request, view=view):
            return True
        raise DrfPermissionDenied


class NestedCodebaseReleaseUnpublishedFilesPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.live:
            raise DrfPermissionDenied('Cannot access unpublished files of published release')
        if request.method == 'GET' and not request.user.has_perm('library.change_codebaserelease', obj=obj):
            raise DrfPermissionDenied('Must have change permission to view release')
        return True


class CodebaseReleaseShareViewSet(CommonViewSetMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    namespace = 'library/codebases/releases/'
    queryset = CodebaseRelease.objects.with_platforms().with_programming_languages()
    lookup_field = 'share_uuid'
    serializer_class = CodebaseReleaseSerializer
    permission_classes = (permissions.AllowAny,)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.accepted_renderer.format == 'html':
            perms = {}
            add_change_delete_perms(instance, perms, request.user)
            return Response({'release': instance, **perms})
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def download(self, request, *args, **kwargs):
        codebase_release = self.get_object()
        if codebase_release.live:
            raise Http404('Cannot download review archive on published release')
        fs_api = codebase_release.get_fs_api()
        try:
            f, mimetype = fs_api.retrieve_review_archive()
            response = FileResponse(f, content_type=mimetype)
            response['Content-Disposition'] = 'attachment; filename={}'.format(codebase_release.archive_filename)
        except FileNotFoundError:
            logger.error("Unable to find review archive for codebase release %s (%s)", codebase_release.pk,
                         codebase_release.get_absolute_url())
            raise Http404()

        return response


class CodebaseReleaseViewSet(CommonViewSetMixin,
                             NoDeleteViewSet):
    namespace = 'library/codebases/releases'
    lookup_field = 'version_number'
    lookup_value_regex = r'\d+\.\d+\.\d+'

    queryset = CodebaseRelease.objects.with_platforms().with_programming_languages()
    pagination_class = SmallResultSetPagination
    permission_classes = (NestedCodebaseReleasePermission, ViewRestrictedObjectPermissions,)

    @property
    def template_name(self):
        # FIXME: figure out why this is needed, CommonViewSetMixin is *supposed* to obviate the need for this
        return 'library/codebases/releases/{}.jinja'.format(self.action)

    def get_serializer_class(self):
        edit = self.request.query_params.get('edit')
        if edit is not None:
            return CodebaseReleaseEditSerializer
        else:
            return CodebaseReleaseSerializer

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
        if request.accepted_renderer.format == 'html':
            perms = {}
            add_change_delete_perms(instance, perms, request.user)
            return Response({'release': instance, **perms})
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
            return queryset.accessible(user=self.request.user).with_submitter().with_codebase()

    @action(detail=True, methods=['put'])
    @transaction.atomic
    def contributors(self, request, **kwargs):
        codebase_release = self.get_object()
        crs = ReleaseContributorSerializer(many=True, data=request.data, context={'release_id': codebase_release.id},
                                           allow_empty=False)
        crs.is_valid(raise_exception=True)
        crs.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def regenerate_share_uuid(self, request, **kwargs):
        codebase_release = self.get_object()
        if codebase_release.live:
            raise ValidationError({'non_field_errors': ['Cannot regenerate share uuid on published release']})
        codebase_release.regenerate_share_uuid()
        return Response(data=request.build_absolute_uri(codebase_release.share_url), status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def publish(self, request, **kwargs):
        version_number = request.data['version_number']
        codebase_release = self.get_object()
        codebase_release.set_version_number(version_number)
        codebase_release.publish()
        return Response(data=codebase_release.version_number, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def notify_reviewers_of_changes(self, request, **kwargs):
        codebase_release = self.get_object()
        review = codebase_release.get_review()
        if review:
            review.author_made_changes()
            if request.accepted_renderer.format == 'html':
                messages.success(request, 'Reviewers notified of changes')
                return HttpResponseRedirect(codebase_release.get_absolute_url())
            return Response(data=review.status, status=status.HTTP_200_OK)
        else:
            msg = 'Must request a review before reviewers can be contacted'
            if request.accepted_renderer.format == 'html':
                response = HttpResponseRedirect(codebase_release.get_absolute_url())
                messages.error(request, msg)
                return response
            return Response(data={'non_field_errors': [msg]},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def request_peer_review(self, request, identifier, version_number):
        codebase_release = get_object_or_404(CodebaseRelease, codebase__identifier=identifier,
                                             version_number=version_number)
        review, created = PeerReview.objects.get_or_create(
            codebase_release=codebase_release,
            defaults={
                'submitter': request.user.member_profile
            }
        )
        if request.accepted_renderer.format == 'html':
            response = HttpResponseRedirect(codebase_release.get_absolute_url())
            messages.success(request, 'Started peer review process')
            return response
        else:
            return Response(data={
                'review_status': review.status,
                'urls': {
                    'review': review.get_absolute_url(),
                    'notify_reviewers_of_changes': codebase_release.get_notify_reviewers_of_changes_url()
                }
            }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    @transaction.atomic
    def download(self, request, **kwargs):
        codebase_release = self.get_object()
        fs_api = codebase_release.get_fs_api()
        try:
            f, mimetype = fs_api.retrieve_archive()
            response = FileResponse(f, content_type=mimetype)
            response['Content-Disposition'] = 'attachment; filename={}'.format(codebase_release.archive_filename)
            codebase_release.record_download(request)
        except FileNotFoundError:
            logger.error("Unable to find archive for codebase release %s (%s)", codebase_release.pk,
                         codebase_release.get_absolute_url())
            raise Http404()

        return response

    @action(detail=True, methods=['get'], renderer_classes=(renderers.JSONRenderer,))
    def download_preview(self, request, **kwargs):
        codebase_release = self.get_object()
        fs_api = codebase_release.get_fs_api()
        contents = fs_api.list_sip_contents()
        return Response(data=contents, status=status.HTTP_200_OK)


class BaseCodebaseReleaseFilesViewSet(viewsets.GenericViewSet):
    lookup_field = 'relpath'
    lookup_value_regex = r'.*'

    queryset = CodebaseRelease.objects.all()
    pagination_class = SmallResultSetPagination
    permission_classes = (NestedCodebaseReleaseUnpublishedFilesPermission, CodebaseReleaseUnpublishedFilePermissions,)
    renderer_classes = (renderers.JSONRenderer,)

    stage = None

    @classmethod
    def get_url_matcher(cls):
        return ''.join([r'codebases/(?P<identifier>[\w\-.]+)',
                        r'/releases/(?P<version_number>\d+\.\d+\.\d+)',
                        r'/files/{}/(?P<category>{})'.format(
                            cls.stage.name,
                            '|'.join(c.name for c in FileCategoryDirectories))])

    def get_queryset(self):
        resolved = resolve(self.request.path)
        identifier = resolved.kwargs['identifier']
        queryset = self.queryset.filter(codebase__identifier=identifier)
        return queryset.accessible(user=self.request.user)

    def get_category(self) -> FileCategoryDirectories:
        category = self.get_parser_context(self.request)['kwargs']['category']
        try:
            return FileCategoryDirectories[category]
        except KeyError:
            raise ValidationError('Target folder name {} invalid. Must be one of {}'.format(category, list(
                d.name for d in FileCategoryDirectories)))

    def get_list_url(self, api):
        raise NotImplementedError

    def list(self, request, *args, **kwargs):
        codebase_release = self.get_object()
        api = codebase_release.get_fs_api()
        category = self.get_category()
        data = api.list(stage=self.stage, category=category)
        if self.stage == StagingDirectories.originals:
            data = [{'name': path, 'identifier': api.get_absolute_url(category=category, relpath=path)}
                    for path in data]
        return Response(data=data, status=status.HTTP_200_OK)

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


class CodebaseReleaseFilesSipViewSet(BaseCodebaseReleaseFilesViewSet):
    stage = StagingDirectories.sip

    def get_list_url(self, api):
        return api.get_sip_list_url


class CodebaseReleaseFilesOriginalsViewSet(BaseCodebaseReleaseFilesViewSet):
    renderer_classes = (renderers.JSONRenderer,)

    stage = StagingDirectories.originals

    def get_list_url(self, api):
        return api.get_originals_list_url

    def create(self, request, *args, **kwargs):
        codebase_release = self.get_object()
        fs_api = codebase_release.get_fs_api()
        category = self.get_category()
        fileobj = request.FILES.get('file')
        if fileobj is None:
            raise ValidationError({'file': ['This field is required']})
        msgs = fs_api.add(content=fileobj, category=category)
        logs, level = msgs.serialize()
        status_code = status.HTTP_400_BAD_REQUEST if level > MessageLevels.info else status.HTTP_202_ACCEPTED
        return Response(status=status_code, data=logs)

    def destroy(self, request, *args, **kwargs):
        relpath = kwargs['relpath']
        codebase_release = self.get_object()
        fs_api = codebase_release.get_fs_api()
        category = self.get_category()
        msgs = fs_api.delete(category=category, relpath=pathlib.Path(relpath))
        logs, level = msgs.serialize()
        status_code = status.HTTP_400_BAD_REQUEST if level > MessageLevels.info else status.HTTP_202_ACCEPTED
        return Response(status=status_code, data=logs)

    @action(detail=False, methods=['DELETE'])
    def clear_category(self, request, **kwargs):
        codebase_release = self.get_object()
        fs_api = codebase_release.get_fs_api()
        category = self.get_category()
        fs_api.clear_category(category)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CodebaseReleaseFormCreateView(FormCreateView):
    namespace = 'library/codebases/releases'
    model = CodebaseRelease
    context_object_name = 'release'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['review_status_enum'] = ReviewStatus
        return context


class CodebaseReleaseFormUpdateView(FormUpdateView):
    namespace = 'library/codebases/releases'
    model = CodebaseRelease
    context_object_name = 'release'

    def get_object(self, queryset=None):
        identifier = self.kwargs['identifier']
        version_number = self.kwargs['version_number']
        return get_object_or_404(queryset or CodebaseRelease,
                                 version_number=version_number,
                                 codebase__identifier=identifier)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['review_status_enum'] = ReviewStatus
        return context


class ContributorFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        qs = request.query_params.get('query')
        return get_search_queryset(qs, queryset)


class ContributorList(generics.ListAPIView):
    queryset = Contributor.objects.all()
    serializer_class = ContributorSerializer
    pagination_class = SmallResultSetPagination
    filter_backends = (ContributorFilter,)
