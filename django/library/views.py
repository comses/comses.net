import json
from allauth.socialaccount.models import SocialAccount
from django.forms import Form
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import resolve, reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import FormView
from django.views.generic.base import RedirectView
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView
from django.views.generic.list import ListView
from ipware import get_client_ip
from rest_framework import (
    viewsets,
    generics,
    status,
    permissions,
    filters,
    mixins,
)
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import (
    PermissionDenied as DrfPermissionDenied,
    ValidationError,
    NotFound,
)
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.models import MemberProfile
from core.permissions import ViewRestrictedObjectPermissions
from core.view_helpers import add_user_retrieve_perms, get_search_queryset
from core.mixins import CommonViewSetMixin, SpamCatcherViewSetMixin
from core.views import (
    FormUpdateView,
    FormCreateView,
    NoDeleteViewSet,
    NoDeleteNoUpdateViewSet,
    HtmlNoDeleteViewSet,
)
from core.pagination import SmallResultSetPagination
from core.serializers import RelatedMemberProfileSerializer
from .github_integration import GithubRepoNameValidator
from .forms import (
    PeerReviewerFeedbackReviewerForm,
    PeerReviewInvitationReplyForm,
    PeerReviewInvitationForm,
    PeerReviewerFeedbackEditorForm,
    PeerReviewFilterForm,
)
from .fs import (
    FileCategoryDirectories,
    StagingDirectories,
    MessageLevels,
)
from .models import (
    Codebase,
    CodebaseGitRemote,
    CodebaseRelease,
    Contributor,
    CodebaseImage,
    License,
    PeerReview,
    PeerReviewer,
    PeerReviewerFeedback,
    PeerReviewInvitation,
    ReviewStatus,
)
from .permissions import CodebaseReleaseUnpublishedFilePermissions
from .serializers import (
    CodebaseGitRemoteSerializer,
    CodebaseSerializer,
    CodebaseReleaseSerializer,
    ContributorSerializer,
    DownloadRequestSerializer,
    PeerReviewerSerializer,
    ReleaseContributorSerializer,
    CodebaseReleaseEditSerializer,
    CodebaseImageSerializer,
    PeerReviewInvitationSerializer,
    PeerReviewFeedbackEditorSerializer,
    PeerReviewEventLogSerializer,
)
from .tasks import build_and_push_codebase_repo

import logging
import pathlib

logger = logging.getLogger(__name__)


def has_permission_to_create_release(request, view):
    user = request.user
    codebase = get_object_or_404(Codebase, identifier=view.kwargs["identifier"])
    if request.method == "POST":
        required_perms = ["library.change_codebase"]
    else:
        required_perms = []
    return user.has_perms(required_perms, obj=codebase)


class PeerReviewDashboardView(PermissionRequiredMixin, ListView):
    template_name = "library/review/dashboard.jinja"
    model = PeerReview
    permission_required = "library.change_peerreview"
    context_object_name = "codebases"
    paginate_by = 15

    def get_form(self):
        return PeerReviewFilterForm(self.request.GET)

    def get_query_params(self):
        form = self.get_form()
        if form.is_valid():
            return form.cleaned_data
        return {}

    def get_queryset(self):
        query_params = self.get_query_params()
        order_by = query_params.get("order_by")
        reviews = PeerReview.objects.with_filters(query_params)
        return Codebase.objects.with_reviews(reviews).order_by(order_by)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = self.get_form()
        query = self.request.GET.copy()
        if "page" in query:
            query.pop("page")
        if query:
            query_string = f"&{query.urlencode()}"
        else:
            query_string = ""
        context["query_string"] = query_string
        return context


class PeerReviewEditorView(PermissionRequiredMixin, DetailView):
    context_object_name = "review"
    model = PeerReview
    permission_required = "library.change_peerreview"
    slug_field = "slug"
    template_name = "library/review/editor_update.jinja"

    def put(self, request, *args, **kwargs):
        request.kwargs = kwargs
        return _change_peer_review_status(request)


class PeerReviewChangeClosedView(PermissionRequiredMixin, DetailView):
    context_object_name = "review"
    model = PeerReview
    permission_required = "library.change_peerreview"
    slug_field = "slug"

    def has_permission(self):
        has_base_permission = super().has_permission()
        if has_base_permission:
            return True
        obj = self.get_object()
        return obj.submitter.user == self.request.user

    def post(self, request, *args, **kwargs):
        review = self.get_object()
        action = request.POST.get("action")
        if action == "close":
            review.close(request.user.member_profile)
        elif action == "reopen":
            review.reopen(request.user.member_profile)
        else:
            raise ValidationError("Invalid action")
        messages.success(
            request,
            (f"Review successfully {action}{'d' if action == 'close' else 'ed'}"),
        )
        return redirect(request.META.get("HTTP_REFERER", ""))


class ChangePeerReviewPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.has_perm("library.change_peerreview"):
            return True
        raise DrfPermissionDenied


class PeerReviewerDashboardView(PermissionRequiredMixin, ListView):
    template_name = "library/review/reviewers.jinja"
    model = PeerReviewer
    permission_required = "library.change_peerreview"


class PeerReviewerFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if view.action != "list":
            return queryset
        query_params = request.query_params
        if query_params.get("query"):
            return get_search_queryset(query_params, queryset)
        return queryset.order_by("member_profile__user__last_name")


class PeerReviewerPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.has_perm("library.change_peerreview"):
            return True
        if view.action == "create" and not self._is_creating_self_reviewer(request):
            raise DrfPermissionDenied
        return True  # drop through to object permission check

    def has_object_permission(self, request, view, obj: PeerReviewer):
        if request.user.has_perm("library.change_peerreview"):
            return True
        if obj.member_profile_id == request.user.member_profile.id:
            return True
        raise DrfPermissionDenied

    def _is_creating_self_reviewer(self, request):
        user_member_profile_id = request.user.member_profile.id
        request_member_profile_id = request.data.get("member_profile_id")
        return user_member_profile_id == request_member_profile_id


class PeerReviewerViewSet(CommonViewSetMixin, NoDeleteViewSet):
    queryset = PeerReviewer.objects.all()
    pagination_class = None
    serializer_class = PeerReviewerSerializer
    permission_classes = (PeerReviewerPermission,)
    filter_backends = (PeerReviewerFilter,)


@api_view(["PUT"])
@permission_classes([])
def _change_peer_review_status(request):
    if not request.user.has_perm("library.change_peerreview"):
        raise PermissionDenied()
    slug = request.kwargs.get("slug")
    review = get_object_or_404(PeerReview, slug=slug)

    raw_status = request.data["status"]
    try:
        new_status = ReviewStatus(raw_status)
    except ValueError:
        raise ValidationError(f"status {raw_status} not valid")
    review.editor_change_review_status(request.user.member_profile, new_status)

    return Response(data={"status": new_status.name}, status=status.HTTP_200_OK)


class PeerReviewInvitationViewSet(NoDeleteNoUpdateViewSet):
    queryset = PeerReviewInvitation.objects.with_reviewer_statistics()
    permission_classes = (ChangePeerReviewPermission,)
    serializer_class = PeerReviewInvitationSerializer
    lookup_url_kwarg = "invitation_slug"

    def get_queryset(self):
        slug = self.kwargs["slug"]
        return self.queryset.filter(review__slug=slug)

    @transaction.atomic
    @action(detail=False, methods=["post"])
    def send_invitation(self, request, slug):
        data = request.data
        candidate_reviewer_id = data.get("id")
        member_profile_id = data.get("member_profile")["id"]
        review = get_object_or_404(PeerReview, slug=slug)
        form_data = dict(review=review.id, editor=request.user.member_profile.id)
        if candidate_reviewer_id is not None:
            form_data["candidate_reviewer"] = member_profile_id
            form_data["reviewer"] = candidate_reviewer_id
        else:
            raise ValidationError("Must specify id of candidate reviewer")
        form = PeerReviewInvitationForm(data=form_data)
        if form.is_valid():
            invitation = form.save()
            invitation.send_candidate_reviewer_email()
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=form.errors)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def resend_invitation(self, request, slug, invitation_slug):
        invitation = get_object_or_404(PeerReviewInvitation, slug=invitation_slug)
        invitation.send_candidate_reviewer_email(resend=True)
        return Response(status=status.HTTP_200_OK)


class PeerReviewInvitationUpdateView(UpdateView):
    context_object_name = "invitation"
    form_class = PeerReviewInvitationReplyForm
    queryset = PeerReviewInvitation.objects.all()
    template_name = "library/review/invitations/update.jinja"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.accepted:
            return redirect(self.object.latest_feedback)
        elif self.object.is_expired:
            error_message = _("This invitation has expired.")
            messages.error(request, error_message)
            raise PermissionDenied(error_message)
        elif self.object.accepted is False:
            messages.warning(request, _("You previously declined this invitation."))
        return super().get(request, *args, **kwargs)

    def get_success_url(self):
        if self.object.accepted:
            return self.object.latest_feedback.get_absolute_url()
        else:
            return self.object.get_absolute_url()


class PeerReviewFeedbackViewSet(NoDeleteNoUpdateViewSet):
    queryset = PeerReviewerFeedback.objects.all()
    serializer_class = PeerReviewFeedbackEditorSerializer

    def get_queryset(self):
        slug = self.kwargs["slug"]
        return self.queryset.filter(invitation__review__slug=slug)


class PeerReviewFeedbackUpdateView(UpdateView):
    context_object_name = "review_feedback"
    form_class = PeerReviewerFeedbackReviewerForm
    template_name = "library/review/feedback/update.jinja"
    pk_url_kwarg = "feedback_id"
    queryset = PeerReviewerFeedback.objects.all()

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.invitation.accepted:
            raise PermissionDenied(
                _("Sorry, you have already declined this invitation")
            )
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        other_feedback = self.object.invitation.feedback_set.exclude(pk=self.object.id)
        context = super().get_context_data(**kwargs)
        context["feedback_set"] = other_feedback
        return context

    def get_success_url(self):
        if self.object.reviewer_submitted:
            messages.info(
                self.request,
                _(
                    "Your review feedback has been submitted. Thank you for taking the time to serve as a "
                    "CoMSES Net reviewer!"
                ),
            )
            return self.object.invitation.reviewer.member_profile.get_absolute_url()
        else:
            messages.info(
                self.request,
                "Your feedback has been saved. Please submit it to the editor when complete.",
            )
            return self.object.get_absolute_url()


class PeerReviewEditorFeedbackUpdateView(UpdateView):
    context_object_name = "review_feedback"
    form_class = PeerReviewerFeedbackEditorForm
    template_name = "library/review/feedback/editor_update.jinja"
    pk_url_kwarg = "feedback_id"
    queryset = PeerReviewerFeedback.objects.all()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # set editor to the currently signed in user initiating this action
        kwargs["editor"] = self.request.user.member_profile
        return kwargs

    def get_success_url(self):
        return self.object.invitation.review.get_absolute_url()


@api_view(["get"])
@permission_classes([])
def list_review_event_log(request, slug):
    review = get_object_or_404(PeerReview, slug=slug)
    if not request.user.has_perm("library.change_peerreview"):
        raise PermissionDenied()
    queryset = review.event_set.order_by("-date_created")[:10]
    serializer = PeerReviewEventLogSerializer(queryset, many=True)
    return Response(serializer.data)


class CodebaseFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if view.action != "list":
            return queryset

        # Get request params
        query_params = request.query_params
        published_start_date = query_params.get("published_after")
        published_end_date = query_params.get("published_before")
        peer_review_status = query_params.get("peer_review_status")
        # platform = query_params.get("platform")
        programming_languages = query_params.getlist("programming_languages")

        tags = query_params.getlist("tags")

        # Handle filtering criteria
        criteria = {}
        if published_start_date and published_end_date:
            if published_start_date < published_end_date:
                criteria.update(
                    first_published_at__range=[published_start_date, published_end_date]
                )
            else:
                logger.warning(
                    "invalid date range: %s, %s",
                    published_start_date,
                    published_end_date,
                )
        elif published_start_date:
            criteria.update(first_published_at__gte=published_start_date)
        elif published_end_date:
            criteria.update(first_published_at__lte=published_end_date)

        if peer_review_status:
            # reviewed_releases = CodebaseRelease.objects.filter(review__isnull=False, codebase=OuterRef('pk'))
            if peer_review_status == "reviewed":
                criteria.update(peer_reviewed=True)
            elif peer_review_status == "not_reviewed":
                criteria.update(peer_reviewed=False)
        if programming_languages:
            # FIXME: this does not work for the same reason tags__name__in does not work, e.g.,
            # https://docs.wagtail.org/en/stable/topics/search/indexing.html#filtering-on-index-relatedfields
            # criteria.update(releases__programming_languages__name__in=programming_languages)
            codebases = Codebase.objects.public(
                releases__programming_languages__name__in=programming_languages
            )
            criteria.update(id__in=codebases.values_list("id", flat=True))

        return get_search_queryset(
            query_params,
            queryset,
            tags=tags,
            criteria=criteria,
        )


class CodebaseViewSet(SpamCatcherViewSetMixin, CommonViewSetMixin, HtmlNoDeleteViewSet):
    lookup_field = "identifier"
    lookup_value_regex = r"[\w\-\.]+"
    pagination_class = SmallResultSetPagination
    queryset = (
        Codebase.objects.with_tags().with_featured_images().order_by("-last_modified")
    )
    filter_backends = (OrderingFilter, CodebaseFilter)
    permission_classes = (ViewRestrictedObjectPermissions,)
    serializer_class = CodebaseSerializer
    ordering_fields = (
        "first_published_at",
        "peer_reviewed",
        "last_modified",
    )
    ordering = ["-first_published_at"]
    context_list_name = "codebases"

    def get_list_context(self, page_or_queryset):
        context = {self.context_list_name: page_or_queryset}
        if self.paginator:
            context["paginator_data"] = self.paginator.get_context_data(context)
        return context

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if request.accepted_renderer.format == "html":
            context = self.get_list_context(page or queryset)

            language_facets = queryset.facet("all_release_programming_languages")
            if language_facets:
                logger.debug(
                    "Appending language_facets to response: %s", language_facets
                )
                context["language_facets"] = json.dumps(language_facets)

            return Response(context)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        if self.action == "list":
            return self.queryset.public()
        # On detail pages we want to see unpublished releases and spam
        return self.queryset.accessible(user=self.request.user)

    def perform_create(self, serializer):
        super().perform_create(serializer)
        codebase = serializer.instance
        return codebase.get_or_create_draft()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # check content negotiation to see if we should redirect to the latest release detail page or if this is an API
        # request for a JSON serialization of this Codebase.
        if request.accepted_media_type == "text/html":
            current_version = instance.latest_version
            if not current_version:
                # no latest_version set, try to retrieve the latest accessible release for this user
                current_version = instance.latest_accessible_release(request.user)
            if not current_version:
                raise Http404
            return redirect(current_version)
        else:
            serializer = self.get_serializer(instance)
            data = add_user_retrieve_perms(instance, serializer.data, request.user)
            return Response(data)


class DevelopmentCodebaseDeleteView(mixins.DestroyModelMixin, CodebaseViewSet):
    lookup_field = "identifier"
    lookup_value_regex = r"[\w\-\.]+"
    pagination_class = SmallResultSetPagination
    queryset = (
        Codebase.objects.with_tags()
        .with_featured_images()
        .order_by("-first_published_at")
    )
    filter_backends = (OrderingFilter, CodebaseFilter)
    ordering_fields = (
        "first_published_at",
        "title",
        "last_modified",
        "peer_reviewed",
        "submitter__last_name",
        "submitter__username",
    )

    def get_queryset(self):
        if self.action == "list":
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
    pattern_name = "library:codebaserelease-detail"

    def get_redirect_url(self, *args, **kwargs):
        simple_version_number = max(1, int(kwargs["version_number"]))
        semver_number = "1.{0}.0".format(simple_version_number - 1)
        kwargs.update(version_number=semver_number)
        return super().get_redirect_url(*args, **kwargs)


class CanChangeCodebase(permissions.BasePermission):
    def has_permission(self, request, view):
        codebase = get_object_or_404(Codebase, identifier=view.kwargs["identifier"])
        return request.user.has_perm("library.change_codebase", codebase)


class CodebaseGitRemoteViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    queryset = CodebaseGitRemote.objects.all()
    permission_classes = (CanChangeCodebase,)
    pagination_class = None
    serializer_class = CodebaseGitRemoteSerializer

    def get_queryset(self):
        resolved = resolve(self.request.path)
        identifier = resolved.kwargs["identifier"]
        return self.queryset.filter(mirror__codebase__identifier=identifier)

    def get_codebase(self):
        try:
            return Codebase.objects.get(identifier=self.kwargs.get("identifier"))
        except Codebase.DoesNotExist:
            raise NotFound("Codebase not found.")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if request.accepted_renderer.format == "html":
            context = {
                "codebase": self.get_codebase(),
                "remotes": queryset,
                "github_org_name": settings.GITHUB_MODEL_LIBRARY_ORG_NAME,
            }
            return Response(
                context,
                template_name="library/codebases/git.jinja",
            )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def submitter_installation_status(self, request, *args, **kwargs):
        codebase = self.get_codebase()
        submitter = codebase.submitter
        installation_url = None
        social_account = submitter.member_profile.get_social_account("github")
        if social_account:
            github_account = {
                "id": social_account.uid,
                "username": social_account.extra_data.get("login"),
                "profile_url": social_account.get_profile_url(),
            }
        else:
            github_account = None

        if github_account:
            if submitter.github_integration_app_installation:
                github_account["installation_id"] = (
                    submitter.github_integration_app_installation.installation_id
                )
            else:
                installation_url = f"https://github.com/apps/{settings.GITHUB_INTEGRATION_APP_NAME}/installations/new?target_id={github_account['id']}"

        return Response(
            data={
                "github_account": github_account,
                "connect_url": reverse("socialaccount_connections"),
                "installation_url": installation_url,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def setup_user_github_remote(self, request, *args, **kwargs):
        codebase = self.get_codebase()
        installation = codebase.submitter.github_integration_app_installation
        return self._setup_github_remote(
            codebase=codebase,
            repo_name=request.data.get("repo_name"),
            owner=installation.github_login,
            is_user_repo=True,
            should_push=True,
            should_archive=True,
            installation=installation,
        )

    @action(detail=False, methods=["post"])
    def setup_org_github_remote(self, request, *args, **kwargs):
        codebase = self.get_codebase()
        return self._setup_github_remote(
            codebase=codebase,
            repo_name=request.data.get("repo_name"),
            owner=settings.GITHUB_MODEL_LIBRARY_ORG_NAME,
            is_user_repo=False,
            should_push=True,
            should_archive=False,
        )

    def _setup_github_remote(
        self,
        codebase: Codebase,
        repo_name: str,
        owner: str,
        is_user_repo: bool,
        should_push: bool,
        should_archive: bool,
        installation=None,
    ):
        if is_user_repo and not installation:
            raise ValidationError(
                "Installation of the Github integration app is required"
            )
        if not codebase.live:
            raise ValidationError("This model does not have any published releases")
        if not repo_name:
            raise ValidationError("Repository name is required")
        try:
            GithubRepoNameValidator.validate(repo_name, installation=installation)
        except ValueError as e:
            raise ValidationError(str(e))

        # create a mirror if it doesn't exist
        if not codebase.git_mirror:
            codebase.create_git_mirror()
        # set up the org remote
        codebase.git_mirror.create_remote(
            owner=owner,
            repo_name=repo_name,
            should_push=should_push,
            is_user_repo=is_user_repo,
            should_archive=should_archive,
        )
        # trigger the build and push task
        build_and_push_codebase_repo(codebase.id, private_repo=settings.DEBUG)
        return Response(
            status=status.HTTP_202_ACCEPTED,
            data="Synchronization process started, this should take only a few seconds. Refresh this page to see the status.",
        )


class CodebaseImageViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    lookup_field = "codebaseimage_id"
    lookup_value_regex = r"\d+"
    queryset = CodebaseImage.objects.all()
    serializer_class = CodebaseImageSerializer
    permission_classes = (CanChangeCodebase,)

    def get_queryset(self):
        resolved = resolve(self.request.path)
        identifier = resolved.kwargs["identifier"]
        return self.queryset.filter(codebase__identifier=identifier)

    def get_object(self, queryset=None):
        queryset = self.filter_queryset(self.get_queryset())
        parser_context = self.get_parser_context(self.request)
        kwargs = parser_context["kwargs"]
        codebase_image_id = kwargs["codebaseimage_id"]
        return get_object_or_404(queryset, id=codebase_image_id)

    def create(self, request, *args, **kwargs):
        codebase = get_object_or_404(Codebase, identifier=kwargs["identifier"])
        fileobj = request.data.get("file")
        if fileobj is None:
            raise ValidationError({"file": ["This field is required"]})
        image = codebase.import_media(fileobj, user=request.user)
        if image is None:
            raise ValidationError(
                [{"msg": {"detail": "file is not an image", "stage": "media"}}]
            )
        codebase.save()
        return Response(status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        codebaseimage = self.get_object()
        codebaseimage.file.storage.delete(codebaseimage.file.path)
        codebaseimage.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["delete"])
    def clear(self, request, *args, **kwargs):
        codebase = get_object_or_404(Codebase, identifier=kwargs["identifier"])
        for codebase_image in codebase.featured_images.all():
            codebase_image.file.storage.delete(codebase_image.file.path)
            codebase_image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CodebaseReleaseDraftView(PermissionRequiredMixin, View):
    def has_permission(self):
        if has_permission_to_create_release(view=self, request=self.request):
            return True
        raise PermissionDenied(
            "Sorry, you do not have permissions to create a new draft release for this codebase."
        )

    def post(self, *args, **kwargs):
        identifier = kwargs["identifier"]
        codebase = get_object_or_404(Codebase, identifier=identifier)
        codebase_release = codebase.get_or_create_draft()
        version_number = codebase_release.version_number
        return redirect(
            "library:codebaserelease-edit",
            identifier=identifier,
            version_number=version_number,
        )


class CodebaseFormCreateView(FormCreateView):
    model = Codebase


class CodebaseFormUpdateView(FormUpdateView):
    model = Codebase
    slug_field = "identifier"
    slug_url_kwarg = "identifier"


class NestedCodebaseReleasePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if has_permission_to_create_release(request=request, view=view):
            return True
        raise DrfPermissionDenied


class NestedCodebaseReleaseUnpublishedFilesPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj: CodebaseRelease):
        if obj.live:
            raise DrfPermissionDenied(
                "Cannot access unpublished files of published release"
            )
        if obj.is_review_complete:
            raise DrfPermissionDenied(
                "Cannot modify unpublished files of a release that has been peer reviewed"
            )
        if request.method == "GET" and not request.user.has_perm(
            "library.change_codebaserelease", obj=obj
        ):
            raise DrfPermissionDenied("Must have change permission to view release")
        return True


def build_archive_download_response(codebase_release, review_archive=False):
    """
    Returns an HttpResponse object that uses nginx to serve our codebase archive zipfiles.
    (https://www.nginx.com/resources/wiki/start/topics/examples/x-accel/)
    :param codebase_release: The specific CodebaseRelease instance archive to download
    :param review_archive: when true we force a rebuild of the CodebaseRelease archive and use the review archive URI
    which is basically just review_archive.zip instead of archive.zip
    :return:
    """
    fs_api = codebase_release.get_fs_api()
    response = HttpResponse()
    response["Content-Type"] = ""
    response["Content-Disposition"] = "attachment; filename={}".format(
        codebase_release.archive_filename
    )
    # response['Content-Length'] = fs_api.archive_size
    archive_uri = fs_api.archive_uri
    archive_absolute_path = fs_api.archivepath
    if review_archive:
        fs_api.build_review_archive()
        archive_absolute_path = fs_api.review_archivepath
        archive_uri = fs_api.review_archive_uri
    #    response['Content-Length'] = fs_api.review_archive_size

    if not archive_absolute_path.exists():
        raise FileNotFoundError
    response["X-Accel-Redirect"] = "/library/internal/{0}".format(archive_uri)
    return response


class CodebaseReleaseShareViewSet(
    CommonViewSetMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    viewset supporting private codebase release share page (e.g., Download for Review)
    """

    namespace = "library/codebases/releases/"
    queryset = CodebaseRelease.objects.with_platforms().with_programming_languages()
    lookup_field = "share_uuid"
    serializer_class = CodebaseReleaseSerializer
    permission_classes = (permissions.AllowAny,)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.accepted_renderer.format == "html":
            perms = {}
            add_user_retrieve_perms(instance, perms, request.user)
            return Response({"release": instance, **perms})
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def download(self, request, *args, **kwargs):
        """
        Download this model archive for review (no need for an interstitial survey)
        """
        codebase_release = self.get_object()
        if codebase_release.live:
            raise Http404("Cannot download review archive on published release")
        try:
            response = build_archive_download_response(
                codebase_release, review_archive=True
            )
        except FileNotFoundError:
            logger.error(
                "Unable to find review archive for codebase release %s (%s)",
                codebase_release.id,
                codebase_release.get_absolute_url(),
            )
            raise Http404

        return response


class CodebaseReleaseViewSet(CommonViewSetMixin, NoDeleteViewSet):
    """
    Handles DRF requests to view, edit, or download the archival information packages for a specific codebase release
    """

    namespace = "library/codebases/releases"
    lookup_field = "version_number"
    lookup_value_regex = r"\d+\.\d+\.\d+"

    queryset = CodebaseRelease.objects.with_platforms().with_programming_languages()
    pagination_class = SmallResultSetPagination
    permission_classes = (
        IsAuthenticatedOrReadOnly,
        NestedCodebaseReleasePermission,
        ViewRestrictedObjectPermissions,
    )

    @property
    def template_name(self):
        # FIXME: figure out why this is needed, CommonViewSetMixin is *supposed* to obviate the need for this
        return "library/codebases/releases/{}.jinja".format(self.action)

    def get_serializer_class(self):
        edit = self.request.query_params.get("edit")
        if edit is not None:
            return CodebaseReleaseEditSerializer
        else:
            return CodebaseReleaseSerializer

    def create(self, request, *args, **kwargs):
        identifier = kwargs["identifier"]
        codebase = get_object_or_404(Codebase, identifier=identifier)
        codebase_release = codebase.get_or_create_draft()
        codebase_release_serializer = self.get_serializer_class()
        serializer = codebase_release_serializer(codebase_release)
        headers = self.get_success_headers(serializer.data)
        return Response(
            status=status.HTTP_201_CREATED, data=serializer.data, headers=headers
        )

    def list(self, request, *args, **kwargs):
        identifier = kwargs["identifier"]
        return redirect("library:codebase-detail", identifier=identifier)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.accepted_renderer.format == "html":
            perms = {}
            add_user_retrieve_perms(instance, perms, request.user)
            return Response({"release": instance, **perms})
        serializer = self.get_serializer(instance)
        data = add_user_retrieve_perms(instance, serializer.data, request.user)
        return Response(data)

    def get_queryset(self):
        resolved = resolve(self.request.path)
        identifier = resolved.kwargs["identifier"]
        queryset = self.queryset.filter(codebase__identifier=identifier)
        if self.action == "list":
            return queryset.public()
        else:
            return (
                queryset.accessible(user=self.request.user)
                .with_submitter()
                .with_codebase()
            )

    @action(detail=True, methods=["put"])
    @transaction.atomic
    def contributors(self, request, **kwargs):
        codebase_release = self.get_object()
        crs = ReleaseContributorSerializer(
            many=True,
            data=request.data,
            context={"release_id": codebase_release.id},
            allow_empty=False,
        )
        crs.is_valid(raise_exception=True)
        crs.save()
        # re-generate codemeta for the parent codebase and only this release
        codebase_release.codebase.save(rebuild_release_metadata=False)
        codebase_release.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def regenerate_share_uuid(self, request, **kwargs):
        codebase_release = self.get_object()
        if codebase_release.live:
            raise ValidationError(
                {
                    "non_field_errors": [
                        "Cannot regenerate share uuid on published release"
                    ]
                }
            )
        codebase_release.regenerate_share_uuid()
        return Response(
            data=request.build_absolute_uri(codebase_release.share_url),
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def publish(self, request, **kwargs):
        version_number = request.data["version_number"]
        codebase_release = self.get_object()
        codebase_release.set_version_number(version_number)
        codebase_release.publish()
        return Response(data=codebase_release.version_number, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def notify_reviewers_of_changes(self, request, **kwargs):
        codebase_release = self.get_object()
        review = codebase_release.get_review()
        if review:
            review.author_resubmitted_changes()
            if request.accepted_renderer.format == "html":
                messages.success(request, "Reviewers notified of changes")
                return HttpResponseRedirect(codebase_release.get_absolute_url())
            return Response(data=review.status, status=status.HTTP_200_OK)
        else:
            msg = "Must request a review before reviewers can be contacted"
            if request.accepted_renderer.format == "html":
                response = HttpResponseRedirect(codebase_release.get_absolute_url())
                messages.error(request, msg)
                return response
            return Response(
                data={"non_field_errors": [msg]}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def request_peer_review(self, request, identifier, version_number):
        """
        If a peer review is requestable (publishable, not reviewed, no related review exists):
        - Create a new "under review" draft release if the release from which the request was made is published
        - Otherwise, update the existing draft release to be "under review"
        - Create a new peer review object and send an email to the author
        """
        codebase_release = get_object_or_404(
            CodebaseRelease,
            codebase__identifier=identifier,
            version_number=version_number,
        )
        codebase_release.validate_publishable()
        existing_review = PeerReview.get_codebase_latest_active_review(
            codebase_release.codebase
        )
        if existing_review:
            review = existing_review
            review_release = existing_review.codebase_release
            created = False
        else:
            if codebase_release.is_draft:
                codebase_release.status = CodebaseRelease.Status.UNDER_REVIEW
                codebase_release.save(update_fields=["status"])
                review_release = codebase_release
            else:
                review_release = (
                    codebase_release.codebase.create_review_draft_from_release(
                        codebase_release
                    )
                )
            review = PeerReview.objects.create(
                codebase_release=review_release,
                submitter=request.user.member_profile,
            )
            review.send_author_requested_peer_review_email()
            created = True

        if created:
            messages.success(request, "Peer review request submitted.")
        else:
            messages.info(
                request,
                "An active peer review already exists for this codebase. Close it below if you wish to open a new one",
            )
        return self.build_review_request_response(request, review_release, review)

    def build_review_request_response(self, request, codebase_release, review):
        if request.accepted_renderer.format == "html":
            return HttpResponseRedirect(codebase_release.get_absolute_url())
        else:
            return Response(
                data={
                    "review_status": review.status,
                    "review_release_url": codebase_release.get_absolute_url(),
                    "urls": {
                        "review": review.get_absolute_url(),
                        "notify_reviewers_of_changes": codebase_release.get_notify_reviewers_of_changes_url(),
                    },
                },
                status=status.HTTP_200_OK,
            )

    @action(detail=True, methods=["post"], permission_classes=[AllowAny])
    @transaction.atomic
    def request_download(self, request, **kwargs):
        """
        Save a download request form and redirect to the download URL
        """
        user = request.user if request.user.is_authenticated else None
        download_request = request.data
        codebase_release = self.get_object()
        referrer = request.META.get("HTTP_REFERER", "")
        client_ip, is_routable = get_client_ip(request)
        download_request.update(
            ip_address=client_ip,
            referrer=referrer,
            user=user.id if user else None,
            release=codebase_release.id,
        )
        serializer = DownloadRequestSerializer(data=download_request)

        if not serializer.is_valid(raise_exception=True):
            raise ValidationError(f"Invalid download request: {download_request}")

        try:
            response = Response(status=status.HTTP_201_CREATED)
            serializer.save()  # records the download + metadata
        except FileNotFoundError:
            logger.error(
                "Unable to find archive for codebase release %s (%s)",
                codebase_release.id,
                codebase_release.get_absolute_url(),
            )
            raise Http404
        return response

    @action(detail=True, methods=["get"])
    @transaction.atomic
    def download(self, request, **kwargs):
        """
        Download the published model archive
        """
        codebase_release = self.get_object()
        try:
            response = build_archive_download_response(codebase_release)
        except FileNotFoundError:
            logger.error(
                "Unable to find archive for codebase release %s (%s)",
                codebase_release.id,
                codebase_release.get_absolute_url(),
            )
            raise Http404

        return response

    @action(detail=True, methods=["get"])
    def download_preview(self, request, **kwargs):
        codebase_release = self.get_object()
        fs_api = codebase_release.get_fs_api()
        contents = fs_api.list_sip_contents()
        return Response(data=contents, status=status.HTTP_200_OK)


class BaseCodebaseReleaseFilesViewSet(viewsets.GenericViewSet):
    lookup_field = "relpath"
    lookup_value_regex = r".*"

    queryset = CodebaseRelease.objects.all()
    pagination_class = SmallResultSetPagination
    permission_classes = (
        NestedCodebaseReleaseUnpublishedFilesPermission,
        CodebaseReleaseUnpublishedFilePermissions,
    )

    stage = None

    @classmethod
    def get_url_matcher(cls):
        return "".join(
            [
                r"codebases/(?P<identifier>[\w\-.]+)",
                r"/releases/(?P<version_number>\d+\.\d+\.\d+)",
                r"/files/{}/(?P<category>{})".format(
                    cls.stage.name, "|".join(c.name for c in FileCategoryDirectories)
                ),
            ]
        )

    def get_queryset(self):
        resolved = resolve(self.request.path)
        identifier = resolved.kwargs["identifier"]
        queryset = self.queryset.filter(codebase__identifier=identifier)
        return queryset.accessible(user=self.request.user)

    def get_category(self) -> FileCategoryDirectories:
        category = self.get_parser_context(self.request)["kwargs"]["category"]
        try:
            return FileCategoryDirectories[category]
        except KeyError:
            raise ValidationError(
                "Target folder name {} invalid. Must be one of {}".format(
                    category, list(d.name for d in FileCategoryDirectories)
                )
            )

    def get_list_url(self, api):
        raise NotImplementedError

    def list(self, request, *args, **kwargs):
        codebase_release = self.get_object()
        api = codebase_release.get_fs_api()
        category = self.get_category()
        data = api.list(stage=self.stage, category=category)
        if self.stage == StagingDirectories.originals:
            data = [
                {
                    "name": path,
                    "identifier": api.get_absolute_url(category=category, relpath=path),
                }
                for path in data
            ]
        return Response(data=data, status=status.HTTP_200_OK)

    def get_object(self, queryset=None):
        # FIXME: should we always override the queryset? This logic is a bit confusing
        queryset = self.filter_queryset(self.get_queryset())
        parser_context = self.get_parser_context(self.request)
        kwargs = parser_context["kwargs"]
        identifier = kwargs["identifier"]
        version_number = kwargs["version_number"]
        obj = get_object_or_404(
            queryset, codebase__identifier=identifier, version_number=version_number
        )

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj


class CodebaseReleaseFilesSipViewSet(BaseCodebaseReleaseFilesViewSet):
    stage = StagingDirectories.sip

    def get_list_url(self, api):
        return api.get_sip_list_url


class CodebaseReleaseFilesOriginalsViewSet(BaseCodebaseReleaseFilesViewSet):
    stage = StagingDirectories.originals

    def get_list_url(self, api):
        return api.get_originals_list_url

    def create(self, request, *args, **kwargs):
        codebase_release = self.get_object()
        fs_api = codebase_release.get_fs_api()
        category = self.get_category()
        fileobj = request.FILES.get("file")
        if fileobj is None:
            raise ValidationError({"file": ["This field is required"]})
        msgs = fs_api.add(content=fileobj, category=category)
        logs, level = msgs.serialize()
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if level > MessageLevels.info
            else status.HTTP_202_ACCEPTED
        )
        return Response(status=status_code, data=logs)

    def destroy(self, request, *args, **kwargs):
        relpath = kwargs["relpath"]
        codebase_release = self.get_object()
        fs_api = codebase_release.get_fs_api()
        category = self.get_category()
        msgs = fs_api.delete(category=category, relpath=pathlib.Path(relpath))
        logs, level = msgs.serialize()
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if level > MessageLevels.info
            else status.HTTP_202_ACCEPTED
        )
        return Response(status=status_code, data=logs)

    @action(detail=False, methods=["DELETE"])
    def clear_category(self, request, **kwargs):
        codebase_release = self.get_object()
        fs_api = codebase_release.get_fs_api()
        category = self.get_category()
        fs_api.clear_category(category)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CodebaseReleaseFormCreateView(FormCreateView):
    namespace = "library/codebases/releases"
    model = CodebaseRelease
    context_object_name = "release"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["review_status_enum_json"] = ReviewStatus.as_json()
        return context


class CodebaseReleaseFormUpdateView(FormUpdateView):
    namespace = "library/codebases/releases"
    model = CodebaseRelease
    context_object_name = "release"

    def get_object(self, queryset=None):
        identifier = self.kwargs["identifier"]
        version_number = self.kwargs["version_number"]
        return get_object_or_404(
            queryset or CodebaseRelease,
            version_number=version_number,
            codebase__identifier=identifier,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["review_status_enum_json"] = ReviewStatus.as_json()
        return context


class ContributorFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        query_params = request.query_params
        return get_search_queryset(query_params, queryset)


class ContributorList(generics.ListAPIView):
    queryset = Contributor.objects.all()
    serializer_class = ContributorSerializer
    pagination_class = SmallResultSetPagination
    filter_backends = (ContributorFilter,)


class CCLicenseChangeView(LoginRequiredMixin, FormView):
    template_name = "library/cc_license_change.jinja"
    form_class = Form  # just a confirmation form, we don't need any fields
    success_message = "Licenses updated successfully."

    # maps CC license SPDX names to a default alternative
    LICENSE_MAPPING = {
        "CC-BY-4.0": "MIT",
        "CC-BY-ND-4.0": "MIT",
        "CC-BY-NC-4.0": "MIT",
        "CC-BY-NC-ND-4.0": "MIT",
        "CC-BY-SA-4.0": "GPL-3.0",
        "CC-BY-NC-SA-4.0": "GPL-3.0",
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_releases = CodebaseRelease.objects.with_cc_license(
            submitter=self.request.user,
        )
        for release in user_releases:
            candidate_license_name = self.LICENSE_MAPPING.get(release.license.name)
            release.candidate_license = License.objects.get(name=candidate_license_name)

        context["user_releases"] = user_releases
        return context

    def form_valid(self, form):
        # update all codebase releases with invalid licenses with their mapped alternative
        try:
            releases_with_cc = CodebaseRelease.objects.with_cc_license(
                submitter=self.request.user
            )
            for release in releases_with_cc:
                candidate_license_name = self.LICENSE_MAPPING.get(release.license.name)
                release.license = License.objects.get(name=candidate_license_name)
                release.save()
            messages.success(
                self.request,
                "Licenses successfully updated. Thanks for making your models more reusable on CoMSES.Net!",
            )
            return super().form_valid(form)
        except Exception as e:
            messages.error(
                self.request,
                "An error occurred while attempting to update your licenses. Please contact us if the problem persists.",
            )
            logger.error("Error updating licenses: %s", e)
            return super().form_invalid(form)

    def get_success_url(self):
        return reverse("core:profile-detail", kwargs={"pk": self.request.user.id})
