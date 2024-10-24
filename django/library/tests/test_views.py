import io
import pathlib
import shutil

from django.conf import settings
from django.test import TestCase, RequestFactory
from django.urls import reverse
from guardian.shortcuts import assign_perm
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from core.tests.base import UserFactory
from core.tests.permissions_base import (
    BaseViewSetTestCase,
    create_perm_str,
    ResponseStatusCodesMixin,
    ApiAccountMixin,
)
from library.forms import PeerReviewerFeedbackReviewerForm
from library.fs import FileCategoryDirectories
from library.models import Codebase, CodebaseRelease, License, PeerReview
from library.tests.base import ReviewSetup
from .base import (
    CodebaseFactory,
    ContributorFactory,
    ReleaseContributorFactory,
    PeerReviewInvitationFactory,
    ReleaseSetup,
)
from ..views import CodebaseViewSet, CodebaseReleaseViewSet, PeerReviewInvitationViewSet

import logging

logger = logging.getLogger(__name__)


class CodebaseViewSetTestCase(BaseViewSetTestCase):
    _view = CodebaseViewSet

    @property
    def serializer_class(self):
        view = self.view_class()
        view.action = self.action
        return view.get_serializer_class()

    def setUp(self):
        self.user_factory = UserFactory()
        submitter = self.user_factory.create()
        self.create_representative_users(submitter)
        self.instance_factory = CodebaseFactory(submitter=submitter)
        self.instance = self.instance_factory.create()
        self.instance.create_release(
            status=CodebaseRelease.Status.PUBLISHED,
            initialize=False,
        )

    def assertResponseNoPermission(self, instance, response):
        if instance.live:
            self.assertResponsePermissionDenied(response)
        else:
            self.assertResponseNotFound(response)

    def check_retrieve_permissions(self, user, instance):
        response = self.client.get(
            instance.get_absolute_url(), HTTP_ACCEPT="application/json", format="json"
        )
        has_perm = user.has_perm(
            create_perm_str(self.model_class(), "view"), obj=instance
        )
        if has_perm:
            self.assertResponseOk(response)
        else:
            self.assertResponseNoPermission(instance, response)

    def check_destroy_method_not_allowed(self, user, instance):
        response = self.client.delete(
            instance.get_absolute_url(), HTTP_ACCEPT="application/json", format="json"
        )
        self.assertResponseMethodNotAllowed(response)

    def check_update_permissions(self, user, instance):
        serialized = self.serializer_class(instance)
        response = self.client.put(
            instance.get_absolute_url(),
            serialized.data,
            HTTP_ACCEPT="application/json",
            format="json",
        )
        has_perm = user.has_perm(create_perm_str(instance, "change"), obj=instance)
        if has_perm:
            self.assertResponseOk(response)
        elif instance.live:
            self.assertResponsePermissionDenied(response)
        else:
            self.assertResponseNotFound(response)

    def check_destroy(self):
        for user in self.users_able_to_login:
            codebase = self.instance_factory.create()
            self.instance.create_release(initialize=False)
            codebase = Codebase.objects.get(pk=codebase.id)
            self.with_logged_in(user, codebase, self.check_destroy_method_not_allowed)

            other_codebase = self.instance_factory.create()
            other_codebase.create_release(initialize=False)
            other_codebase = Codebase.objects.get(pk=other_codebase.id)
            assign_perm(
                create_perm_str(other_codebase, "delete"),
                user_or_group=user,
                obj=other_codebase,
            )
            self.with_logged_in(
                user, other_codebase, self.check_destroy_method_not_allowed
            )

        codebase = self.instance_factory.create()
        codebase.create_release(initialize=False)
        codebase = Codebase.objects.get(pk=codebase.id)
        response = self.client.delete(codebase.get_absolute_url())
        self.assertResponseMethodNotAllowed(response)

    def check_update(self):
        for user in self.users_able_to_login:
            codebase = self.instance_factory.create()
            codebase.create_release(initialize=False)
            codebase = Codebase.objects.get(pk=codebase.id)
            self.with_logged_in(user, codebase, self.check_update_permissions)
            assign_perm(
                create_perm_str(self.instance, "change"),
                user_or_group=user,
                obj=codebase,
            )
            self.with_logged_in(user, codebase, self.check_update_permissions)

        codebase = self.instance_factory.create()
        codebase.create_release(initialize=False)
        codebase = Codebase.objects.get(pk=codebase.id)
        self.check_update_permissions(self.anonymous_user, codebase)

    def test_retrieve(self):
        self.action = "retrieve"
        self.check_retrieve()

    def test_update(self):
        self.action = "update"
        self.check_update()

    def test_destroy(self):
        self.action = "destroy"
        self.check_destroy()

    def test_create(self):
        self.action = "create"
        self.check_create()

    def test_list(self):
        self.action = "list"
        self.check_list()


class CodebaseReleaseViewSetTestCase(BaseViewSetTestCase):
    _view = CodebaseReleaseViewSet

    def setUp(self):
        self.user_factory = UserFactory()
        self.submitter = self.user_factory.create(username="submitter")
        self.other_user = self.user_factory.create(username="other_user")
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = codebase_factory.create()
        self.codebase_release = self.codebase.create_release(
            status=CodebaseRelease.Status.PUBLISHED, initialize=False
        )
        self.path = self.codebase_release.get_list_url()

    def test_release_creation_only_if_codebase_change_permission(self):
        response = self.client.post(
            path=self.path, format="json", HTTP_ACCEPT="application/json"
        )
        self.assertResponsePermissionDenied(response)

        self.login(self.other_user, self.user_factory.password)
        response_other_user = self.client.post(
            path=self.path, data=None, HTTP_ACCEPT="application/json", format="json"
        )
        self.assertResponsePermissionDenied(response_other_user)

        self.login(self.submitter, self.user_factory.password)
        response_submitter = self.client.post(
            path=self.path, HTTP_ACCEPT="application/json", format="json"
        )
        self.assertResponseCreated(response_submitter)

    def test_destroy_method_not_allowed(self):
        path = self.codebase_release.get_absolute_url()

        response = self.client.delete(path=path)
        self.assertResponsePermissionDenied(response)

        self.client.login(
            username=self.other_user.username, password=self.user_factory.password
        )
        response = self.client.delete(path=path, HTTP_ACCEPT="application/json")
        self.assertResponseMethodNotAllowed(response)

        self.client.login(
            username=self.submitter.username, password=self.user_factory.password
        )
        response = self.client.delete(path=path, HTTP_ACCEPT="application/json")
        self.assertResponseMethodNotAllowed(response)

    def test_request_peer_review_from_draft(self):
        self.client.login(
            username=self.submitter.username, password=self.user_factory.password
        )
        draft_release = ReleaseSetup.setUpPublishableDraftRelease(self.codebase)
        response = self.client.post(
            draft_release.get_request_peer_review_url(),
            HTTP_ACCEPT="application/json",
        )

        logger.fatal(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            CodebaseRelease.objects.get(id=draft_release.id).status,
            CodebaseRelease.Status.UNDER_REVIEW,
        )
        self.assertTrue(
            PeerReview.objects.filter(codebase_release=draft_release).exists()
        )

    def test_request_peer_review_from_published(self):
        self.client.login(
            username=self.submitter.username, password=self.user_factory.password
        )
        draft_release = ReleaseSetup.setUpPublishableDraftRelease(self.codebase)
        draft_release.publish()

        response = self.client.post(
            draft_release.get_request_peer_review_url(),
            HTTP_ACCEPT="application/json",
        )

        under_review_release = draft_release.codebase.latest_accessible_release(
            self.submitter
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(
            draft_release.id,
            under_review_release.id,
        )
        self.assertTrue(
            PeerReview.objects.filter(codebase_release=under_review_release).exists()
        )

    def test_request_peer_review_existing_review(self):
        self.client.login(
            username=self.submitter.username, password=self.user_factory.password
        )
        first_release = ReleaseSetup.setUpPublishableDraftRelease(self.codebase)
        PeerReview.objects.create(
            codebase_release=first_release, submitter=self.submitter.member_profile
        )
        second_release = ReleaseSetup.setUpPublishableDraftRelease(self.codebase)

        response = self.client.post(
            second_release.get_request_peer_review_url(),
            HTTP_ACCEPT="application/json",
        )

        # this returns a 200 success, might be better to 302 but that needs some refactoring
        self.assertEqual(
            PeerReview.objects.filter(codebase_release=first_release).count(), 1
        )
        self.assertEqual(
            PeerReview.objects.filter(codebase_release=second_release).count(), 0
        )

    def test_request_peer_review_existing_closed_review(self):
        self.client.login(
            username=self.submitter.username, password=self.user_factory.password
        )
        first_release = ReleaseSetup.setUpPublishableDraftRelease(self.codebase)
        pr = PeerReview.objects.create(
            codebase_release=first_release, submitter=self.submitter.member_profile
        )
        pr.close(self.submitter.member_profile)
        second_release = ReleaseSetup.setUpPublishableDraftRelease(self.codebase)

        response = self.client.post(
            second_release.get_request_peer_review_url(),
            HTTP_ACCEPT="application/json",
        )

        self.assertTrue(
            PeerReview.objects.filter(codebase_release=second_release).exists()
        )


class CodebaseReleaseUnpublishedFilesTestCase(
    ApiAccountMixin, ResponseStatusCodesMixin, TestCase
):
    """Test file handling for creating a release. Only user with change permission on a unpublished release should be
    able to list, destroy or create files. No user should be able to create or destroy files from a published release
    """

    def setUp(self):
        self.user_factory = UserFactory()
        self.submitter = self.user_factory.create(username="submitter")
        self.superuser = self.user_factory.create(
            username="superuser", is_superuser=True
        )
        self.other_user = self.user_factory.create(username="other_user")
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = codebase_factory.create()
        self.codebase_release = self.codebase.create_release(
            status=CodebaseRelease.Status.UNPUBLISHED,
            initialize=False,
        )

    def test_upload_file(self):
        api = self.codebase_release.get_fs_api()

        # Unpublished codebase release permissions
        response = self.client.post(
            api.get_originals_list_url(category=FileCategoryDirectories.code)
        )
        self.assertResponseNotFound(response)
        for user, expected_status_code in [
            (self.submitter, status.HTTP_400_BAD_REQUEST),
            (self.superuser, status.HTTP_400_BAD_REQUEST),
            (self.other_user, status.HTTP_404_NOT_FOUND),
        ]:
            self.login(user, self.user_factory.password)
            response = self.client.post(
                api.get_originals_list_url(category=FileCategoryDirectories.code),
                HTTP_ACCEPT="application/json",
            )
            self.assertEqual(
                response.status_code,
                expected_status_code,
                msg="{} {}".format(repr(user), response.data),
            )

        self.codebase_release.status = CodebaseRelease.Status.PUBLISHED
        self.codebase_release.save()

        # Published codebase release permissions
        self.client.logout()
        response = self.client.post(
            api.get_originals_list_url(category=FileCategoryDirectories.code)
        )
        self.assertResponsePermissionDenied(response)
        for user, expected_status_code in [
            (self.submitter, status.HTTP_403_FORBIDDEN),
            (self.superuser, status.HTTP_403_FORBIDDEN),
            (self.other_user, status.HTTP_403_FORBIDDEN),
        ]:
            self.login(user, self.user_factory.password)
            response = self.client.post(
                api.get_originals_list_url(category=FileCategoryDirectories.code),
                HTTP_ACCEPT="application/json",
            )
            self.assertEqual(
                response.status_code,
                expected_status_code,
                msg="{} {}".format(repr(user), response.data),
            )

    def test_list_files(self):
        api = self.codebase_release.get_fs_api()

        # Unpublished codebase release permissions
        response = self.client.get(
            api.get_originals_list_url(category=FileCategoryDirectories.code)
        )
        self.assertResponseNotFound(response)
        for user, expected_status_code in [
            (self.submitter, status.HTTP_200_OK),
            (self.superuser, status.HTTP_200_OK),
            (self.other_user, status.HTTP_404_NOT_FOUND),
        ]:
            self.login(user, self.user_factory.password)
            response = self.client.get(
                api.get_originals_list_url(FileCategoryDirectories.code),
                HTTP_ACCEPT="application/json",
            )
            self.assertEqual(
                response.status_code,
                expected_status_code,
                msg="{} {}".format(repr(user), response.data),
            )

        self.codebase_release.status = CodebaseRelease.Status.PUBLISHED
        self.codebase_release.save()
        self.client.logout()

        # Published codebase release permissions
        response = self.client.get(
            api.get_originals_list_url(FileCategoryDirectories.code)
        )
        self.assertResponsePermissionDenied(response)
        for user, expected_status_code in [
            (self.submitter, status.HTTP_403_FORBIDDEN),
            (self.superuser, status.HTTP_403_FORBIDDEN),
            (self.other_user, status.HTTP_403_FORBIDDEN),
        ]:
            self.login(user, self.user_factory.password)
            response = self.client.get(
                api.get_originals_list_url(FileCategoryDirectories.code),
                HTTP_ACCEPT="application/json",
            )
            self.assertEqual(
                response.status_code,
                expected_status_code,
                msg=f"{user} {response.data}",
            )

    def test_delete_file(self):
        path_to_foo = pathlib.Path("foo.txt")
        api = self.codebase_release.get_fs_api()
        # Unpublished codebase release permissions
        response = self.client.delete(
            api.get_absolute_url(
                category=FileCategoryDirectories.code, relpath=path_to_foo
            )
        )
        self.assertResponseNotFound(response)
        for user, expected_status_code in [
            (self.submitter, status.HTTP_400_BAD_REQUEST),
            (self.superuser, status.HTTP_400_BAD_REQUEST),
            (self.other_user, status.HTTP_404_NOT_FOUND),
        ]:
            self.login(user, self.user_factory.password)
            response = self.client.delete(
                api.get_absolute_url(
                    category=FileCategoryDirectories.code, relpath=path_to_foo
                ),
                HTTP_ACCEPT="application/json",
            )
            self.assertEqual(response.status_code, expected_status_code, msg=repr(user))

        self.codebase_release.status = CodebaseRelease.Status.PUBLISHED
        self.codebase_release.save()
        self.client.logout()

        # Published codebase release permissions
        response = self.client.delete(
            api.get_absolute_url(
                category=FileCategoryDirectories.code, relpath=path_to_foo
            )
        )
        self.assertResponsePermissionDenied(response)
        for user, expected_status_code in [
            (self.submitter, status.HTTP_403_FORBIDDEN),
            (self.superuser, status.HTTP_403_FORBIDDEN),
            (self.other_user, status.HTTP_403_FORBIDDEN),
        ]:
            self.login(user, self.user_factory.password)
            response = self.client.delete(
                api.get_absolute_url(FileCategoryDirectories.code, path_to_foo),
                HTTP_ACCEPT="application/json",
            )
            self.assertEqual(response.status_code, expected_status_code, msg=repr(user))


class CodebaseReleaseDraftViewTestCase(
    ApiAccountMixin, ResponseStatusCodesMixin, TestCase
):
    def setUp(self):
        self.user_factory = UserFactory()
        self.submitter = self.user_factory.create(username="submitter")
        self.other_user = self.user_factory.create(username="other_user")
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = codebase_factory.create()
        self.codebase_release = self.codebase.create_release(
            status=CodebaseRelease.Status.PUBLISHED, initialize=False
        )
        self.path = self.codebase.get_draft_url()

    def test_release_creation_only_if_codebase_change_permission(self):
        response = self.client.post(path=self.path)
        self.assertResponsePermissionDenied(response)

        self.login(self.other_user, self.user_factory.password)
        response_other_user = self.client.post(path=self.path)
        self.assertResponsePermissionDenied(response_other_user)

        self.login(self.submitter, self.user_factory.password)
        response_submitter = self.client.post(path=self.path)
        self.assertResponseFound(response_submitter)


class ViewUrlRegexTestCase(TestCase):
    def test_download_unpublished(self):
        reverse(
            "library:codebaserelease-original-files-detail",
            kwargs={
                "version_number": "1.0.0",
                "identifier": "a822d39c-3e62-45a4-bf87-3340f524910c",
                "relpath": "converted/206/3-4/round3.17.save-bot-data.csv",
                "category": "code",
            },
        )


class CodebaseReleasePublishTestCase(TestCase):
    client_class = APIClient

    def setUp(self):
        self.user_factory = UserFactory()
        self.submitter = self.user_factory.create()
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = codebase_factory.create()
        # Want to test get_fs_api creates the file system even if file system is not initialized properly
        self.codebase_release = self.codebase.create_release(initialize=False)
        contributor_factory = ContributorFactory(user=self.submitter)
        self.contributor = contributor_factory.create()
        self.release_contributor_factory = ReleaseContributorFactory(
            codebase_release=self.codebase_release
        )

    def test_publish_codebaserelease(self):
        with self.assertRaises(ValidationError):
            self.codebase_release.publish()

        self.release_contributor_factory.create(self.contributor)
        with self.assertRaises(ValidationError):
            self.codebase_release.publish()

        self.client.login(
            username=self.submitter.username, password=self.user_factory.password
        )
        response = self.client.post(
            self.codebase_release.regenerate_share_url, HTTP_ACCEPT="application/json"
        )
        self.assertEqual(response.status_code, 200)

        code_file = io.BytesIO(bytes("Hello world!", "utf8"))
        code_file.name = "test.nlogo"

        docs_file = io.BytesIO(bytes("A new model", "utf8"))
        docs_file.name = "README.md"

        api = self.codebase_release.get_fs_api()
        api.add(content=code_file, category=FileCategoryDirectories.code)
        api.add(content=docs_file, category=FileCategoryDirectories.docs)

        with self.assertRaises(
            ValidationError, msg="Codebase has no metadata, should fail publish"
        ):
            self.codebase_release.publish()

        # FIXME: add metadata to codebase release and verify that publish doesn't raise a ValidationError
        self.codebase_release.os = "Windows"
        self.assertRaises(ValidationError, lambda: self.codebase_release.publish())

        self.codebase_release.license = License.objects.create(
            name="0BSD", url="https://spdx.org/licenses/0BSD.html"
        )
        self.assertRaises(ValidationError, lambda: self.codebase_release.publish())

        self.codebase_release.programming_languages.add("Java")

        self.codebase_release.publish()

        download_response = self.client.get(
            self.codebase_release.get_review_download_url()
        )
        self.assertEqual(
            download_response.status_code,
            404,
            msg="Published model should not allow access to a review download URL",
        )
        response = self.client.post(
            self.codebase_release.regenerate_share_url, HTTP_ACCEPT="application/json"
        )
        self.assertEqual(
            response.status_code,
            400,
            msg="Published model should not permit regeneration of a unique share URL",
        )


class CodebaseRenderPageTestCase(TestCase):
    def setUp(self):
        user_factory = UserFactory()
        self.submitter = user_factory.create()
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = codebase_factory.create()

    def test_list(self):
        response = self.client.get(
            reverse(
                "library:codebase-detail",
                kwargs={"identifier": self.codebase.identifier},
            )
        )
        self.assertTrue(response.status_code, 200)


class CodebaseReleaseRenderPageTestCase(TestCase):
    def setUp(self):
        user_factory = UserFactory()
        self.submitter = user_factory.create()
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        contributor_factory = ContributorFactory(user=self.submitter)
        contributor = contributor_factory.create(user=self.submitter)

        self.codebase = codebase_factory.create(submitter=self.submitter)
        self.codebase_release = self.codebase.create_release(initialize=False)
        release_contributor_factory = ReleaseContributorFactory(
            codebase_release=self.codebase_release
        )
        release_contributor_factory.create(contributor=contributor)

    def test_detail(self):
        response = self.client.get(
            reverse(
                "library:codebaserelease-detail",
                kwargs={
                    "identifier": self.codebase.identifier,
                    "version_number": self.codebase_release.version_number,
                },
            )
        )
        self.assertTrue(response.status_code, True)


class CodebaseSearchTestCase(TestCase):
    def setUp(self):
        user_factory = UserFactory()
        self.submitter = user_factory.create()
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = codebase_factory.create()

    def test_search(self):
        response = self.client.get(
            reverse("library:codebase-list"),
            {"q": "fauna"},
        )
        self.assertEqual(response.status_code, 200)


class PeerReviewInvitationTestCase(ReviewSetup, ResponseStatusCodesMixin, TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.setUpReviewData()

    def setUp(self):
        invitation_factory = PeerReviewInvitationFactory(
            editor=self.editor, reviewer=self.reviewer, review=self.review
        )
        self.invitation = invitation_factory.create()

    def test_accept_invitation_multiple_times(self):
        url = self.invitation.get_absolute_url()
        get_invitation_page_response = self.client.get(url)
        self.assertResponseOk(get_invitation_page_response)
        post_invitation_page_response = self.client.post(url, data={"accepted": True})
        self.assertResponseFound(post_invitation_page_response)

        feedback = self.invitation.latest_feedback

        get_invitation_page_response_again = self.client.get(url)
        # going back to the invitation page after accepting redirects to latest feedback
        self.assertRedirects(
            get_invitation_page_response_again, feedback.get_absolute_url()
        )
        post_invitation_page_response_again = self.client.post(
            url, data={"accepted": True}
        )
        self.assertRedirects(
            post_invitation_page_response_again, feedback.get_absolute_url()
        )

    def test_accept_after_decline(self):
        url = self.invitation.get_absolute_url()
        get_invitation_page_response = self.client.get(url)
        self.assertResponseOk(get_invitation_page_response)
        post_invitation_page_response = self.client.post(url, data={"accepted": False})
        self.assertResponseFound(post_invitation_page_response)
        self.assertRedirects(post_invitation_page_response, url)

        get_invitation_page_response_again = self.client.get(url)
        self.assertContains(
            get_invitation_page_response_again, "declined this invitation"
        )
        # candidate reviewers are allowed to decline again
        post_invitation_page_response_again = self.client.post(
            url, data={"accepted": False}
        )
        self.assertRedirects(post_invitation_page_response_again, url)
        # candidate reviewers are allowed to accept after declining
        accept_invitation_response = self.client.post(url, data={"accepted": True})
        self.assertRedirects(
            accept_invitation_response,
            self.invitation.latest_feedback.get_absolute_url(),
        )

    def test_resend_invitation(self):
        # date_sent field should be updated when resending an invitation
        date_sent = self.invitation.date_sent
        request = RequestFactory().post("/invitations/", data={})
        view = PeerReviewInvitationViewSet()
        view.resend_invitation(request, slug=None, invitation_slug=self.invitation.slug)
        self.invitation.refresh_from_db()
        self.assertGreater(self.invitation.date_sent, date_sent)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()


class PeerReviewFeedbackTestCase(ReviewSetup, ResponseStatusCodesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.setUpReviewData()
        invitation_factory = PeerReviewInvitationFactory(
            editor=cls.editor, reviewer=cls.reviewer, review=cls.review
        )
        cls.invitation = invitation_factory.create()

    def setUp(self):
        self.feedback = self.invitation.latest_feedback

    def test_can_only_access_feedback_if_invitation_accepted(self):
        feedback = self.invitation.accept()
        response_accept = self.client.get(feedback.get_absolute_url())
        self.assertResponseOk(response_accept)

        self.invitation.decline()
        response_decline = self.client.get(feedback.get_absolute_url())
        self.assertResponsePermissionDenied(response_decline)

    def test_cannot_update_feedback_on_complete_review(self):
        feedback = self.invitation.accept()
        self.review.set_complete_status(self.editor)
        data = PeerReviewerFeedbackReviewerForm(instance=feedback).initial
        form = PeerReviewerFeedbackReviewerForm(data.copy(), instance=feedback)
        self.assertFalse(form.is_valid())


def tearDownModule():
    shutil.rmtree(settings.LIBRARY_ROOT, ignore_errors=True)
