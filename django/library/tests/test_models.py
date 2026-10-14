import logging
import pathlib
import semver
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.tests.base import UserFactory, BaseModelTestCase
from .base import (
    CodebaseFactory,
    ContributorFactory,
    ReleaseContributorFactory,
    ReleaseSetup,
)
from ..models import (
    ProgrammingLanguage,
    ReleaseLanguage,
    Codebase,
    CodebaseRelease,
    License,
    PeerReview,
    PeerReviewEvent,
    PeerReviewer,
    PeerReviewerFeedback,
    ReviewStatus,
)

logger = logging.getLogger(__name__)


class PeerReviewTransitionTest(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        self.codebase = CodebaseFactory(submitter=self.user).create()
        self.release = ReleaseSetup.setUpPublishableDraftRelease(self.codebase)
        self.release.status = CodebaseRelease.Status.UNDER_REVIEW
        self.release.save(update_fields=["status"])
        self.review = PeerReview.objects.create(
            codebase_release=self.release, submitter=self.user.member_profile
        )

    def create_invitation(self, accepted=True):
        reviewer = PeerReviewer.objects.create(member_profile=self.user.member_profile)
        return self.review.invitation_set.create(
            editor=self.user.member_profile,
            candidate_reviewer=self.user.member_profile,
            reviewer=reviewer,
            accepted=accepted,
        )

    @patch("library.models.PeerReview.send_author_requested_peer_review_email")
    def test_cancel_discards_only_drafts_and_reuses_invitation_links(self, notify):
        invitation = self.create_invitation()
        old_feedback = invitation.feedback_set.create(
            runnable_comments="Unsubmitted work"
        )
        invitation_url = invitation.get_absolute_url()
        sent_at = invitation.date_sent
        self.review.close(self.user.member_profile)
        self.assertFalse(
            PeerReviewerFeedback.objects.filter(pk=old_feedback.pk).exists()
        )
        with self.assertRaises(ValidationError):
            old_feedback.validate_editable()
        with self.assertRaises(ValidationError):
            invitation.latest_feedback
        self.assertEqual(invitation.feedback_set.count(), 0)
        self.assertTrue(self.review.reopen(self.user.member_profile))
        invitation.refresh_from_db()
        self.assertIsNone(invitation.accepted)
        self.assertEqual(invitation.get_absolute_url(), invitation_url)
        self.assertEqual(invitation.date_sent, sent_at)
        self.assertEqual(invitation.feedback_set.count(), 0)
        fresh_feedback = invitation.accept()
        self.assertNotEqual(fresh_feedback.pk, old_feedback.pk)
        self.assertFalse(fresh_feedback.reviewer_submitted)
        self.assertEqual(self.review.status, ReviewStatus.AWAITING_REVIEWER_FEEDBACK)
        self.assertFalse(self.review.reopen(self.user.member_profile))
        self.assertEqual(invitation.feedback_set.count(), 1)
        notify.assert_called_once()

    def test_reopen_discards_drafts_retained_by_legacy_close(self):
        invitation = self.create_invitation()
        feedback = invitation.feedback_set.create(runnable_comments="Old draft")
        PeerReview.objects.filter(pk=self.review.pk).update(closed=True)
        self.assertTrue(self.review.reopen(self.user.member_profile))
        self.assertFalse(PeerReviewerFeedback.objects.filter(pk=feedback.pk).exists())
        invitation.refresh_from_db()
        self.assertIsNone(invitation.accepted)
        fresh_feedback = invitation.accept()
        self.assertNotEqual(fresh_feedback.pk, feedback.pk)
        self.assertFalse(fresh_feedback.reviewer_submitted)

    def test_cancel_preserves_submitted_feedback_and_editor_notes(self):
        invitation = self.create_invitation()
        for field, value in (
            ("reviewer_submitted", True),
            ("private_editor_notes", "Editorial decision notes"),
            ("notes_to_author", "An editorial decision was communicated"),
        ):
            with self.subTest(field=field):
                feedback = invitation.feedback_set.create(**{field: value})
                with self.assertRaises(ValidationError):
                    self.review.close(self.user.member_profile)
                self.review.refresh_from_db()
                self.assertFalse(self.review.closed)
                feedback.refresh_from_db()
                self.assertTrue(
                    type(feedback)
                    .objects.filter(pk=feedback.pk, **{field: value})
                    .exists()
                )
                self.assertEqual(self.review.event_set.count(), 0)
                feedback.delete()

    def test_cancel_preserves_history_of_submission_or_editorial_decisions(self):
        for action in (
            PeerReviewEvent.REVIEWER_FEEDBACK_SUBMITTED,
            PeerReviewEvent.REVISIONS_REQUESTED,
            PeerReviewEvent.RELEASE_CERTIFIED,
        ):
            with self.subTest(action=action):
                event = self.review.log(
                    "Prior review work", action, self.user.member_profile
                )
                with self.assertRaises(ValidationError):
                    self.review.close(self.user.member_profile)
                self.review.refresh_from_db()
                self.assertFalse(self.review.closed)
                self.assertEqual(self.review.event_set.count(), 1)
                event.delete()

    def test_historically_closed_review_with_submitted_feedback_cannot_reopen(self):
        invitation = self.create_invitation()
        feedback = invitation.feedback_set.create(reviewer_submitted=True)
        PeerReview.objects.filter(pk=self.review.pk).update(closed=True)
        with self.assertRaises(ValidationError):
            self.review.reopen(self.user.member_profile)
        self.review.refresh_from_db()
        self.assertTrue(self.review.closed)
        feedback.refresh_from_db()
        self.assertTrue(feedback.reviewer_submitted)

    def test_author_changes_status_requires_curatorial_cancellation(self):
        self.review.editor_change_review_status(
            self.user.member_profile, ReviewStatus.AWAITING_AUTHOR_CHANGES
        )
        with self.assertRaises(ValidationError):
            self.review.close(self.user.member_profile)
        self.review.refresh_from_db()
        self.assertFalse(self.review.closed)

    def test_expired_invitations_require_resending_after_reopen(self):
        invitation = self.create_invitation()
        sent_at = timezone.now() - timedelta(
            days=settings.PEER_REVIEW_INVITATION_EXPIRATION + 1
        )
        type(invitation).objects.filter(pk=invitation.pk).update(date_sent=sent_at)
        self.review.close(self.user.member_profile)
        self.review.reopen(self.user.member_profile)
        invitation.refresh_from_db()
        self.assertEqual(invitation.date_sent, sent_at)
        self.assertTrue(invitation.is_expired)
        with self.assertRaises(ValidationError):
            invitation.accept()
        invitation.send_candidate_reviewer_email(resend=True)
        sent_at = invitation.date_sent
        feedback = invitation.accept()
        invitation.refresh_from_db()
        self.assertEqual(invitation.date_sent, sent_at)
        self.assertFalse(invitation.is_expired)
        self.assertEqual(invitation.accept().pk, feedback.pk)
        self.assertEqual(invitation.feedback_set.count(), 1)
        self.assertEqual(
            self.review.event_set.filter(
                action=PeerReviewEvent.INVITATION_ACCEPTED.name
            ).count(),
            1,
        )

    def test_reopen_rejects_completed_review_without_relying_on_release_status(self):
        self.review.status = ReviewStatus.COMPLETE
        self.review.closed = True
        self.review.save()
        with self.assertRaises(ValidationError):
            self.review.reopen(self.user.member_profile)
        self.review.refresh_from_db()
        self.assertTrue(self.review.closed)
        self.assertEqual(self.review.event_set.count(), 0)

    def test_reopen_rejects_another_active_review(self):
        self.review.close(self.user.member_profile)
        other_release = self.codebase.create_release(initialize=False)
        PeerReview.objects.create(
            codebase_release=other_release, submitter=self.user.member_profile
        )
        with self.assertRaises(ValidationError):
            self.review.reopen(self.user.member_profile)
        self.review.refresh_from_db()
        self.assertTrue(self.review.closed)

    def test_reopen_requires_review_ready_metadata(self):
        self.review.close(self.user.member_profile)
        self.release.license = None
        self.release.save(update_fields=["license"])
        with self.assertRaises(ValidationError):
            self.review.reopen(self.user.member_profile)
        self.review.refresh_from_db()
        self.assertTrue(self.review.closed)

    def test_status_selector_cannot_certify_or_demote_completed_reviews(self):
        with self.assertRaises(ValidationError):
            self.review.editor_change_review_status(
                self.user.member_profile, ReviewStatus.COMPLETE
            )
        self.review.status = ReviewStatus.COMPLETE
        self.review.save()
        with self.assertRaises(ValidationError):
            self.review.editor_change_review_status(
                self.user.member_profile, ReviewStatus.AWAITING_REVIEWER_FEEDBACK
            )

    @patch("library.models.PeerReview.send_model_certified_email")
    def test_certification_is_idempotent(self, notify):
        self.assertTrue(self.review.set_complete_status(self.user.member_profile))
        self.assertFalse(self.review.set_complete_status(self.user.member_profile))
        self.release.refresh_from_db()
        self.assertEqual(self.release.status, CodebaseRelease.Status.REVIEW_COMPLETE)
        self.assertTrue(self.release.peer_reviewed)
        self.assertEqual(
            self.review.event_set.filter(
                action=PeerReviewEvent.RELEASE_CERTIFIED.name
            ).count(),
            1,
        )
        notify.assert_called_once()

    def test_closed_reviews_reject_certification_and_status_changes(self):
        self.review.close(self.user.member_profile)
        with self.assertRaises(ValidationError):
            self.review.set_complete_status(self.user.member_profile)
        with self.assertRaises(ValidationError):
            self.review.editor_change_review_status(
                self.user.member_profile, ReviewStatus.AWAITING_EDITOR_FEEDBACK
            )

    def test_repeated_close_and_status_change_do_not_duplicate_events(self):
        self.assertFalse(
            self.review.editor_change_review_status(
                self.user.member_profile, self.review.status
            )
        )
        self.assertTrue(self.review.close(self.user.member_profile))
        self.assertFalse(self.review.close(self.user.member_profile))
        self.assertEqual(self.review.event_set.count(), 1)


class CodebaseTest(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        self.c1 = Codebase.objects.create(
            title="Test codebase",
            description="Test codebase description",
            identifier="c1",
            submitter=self.user,
        )

    def test_base_dir(self):
        self.assertEqual(
            self.c1.base_library_dir,
            pathlib.Path(settings.LIBRARY_ROOT, str(self.c1.uuid)),
        )
        self.assertEqual(
            self.c1.base_git_dir,
            pathlib.Path(settings.REPOSITORY_ROOT, str(self.c1.uuid)),
        )

    def test_create_release(self):
        release = ReleaseSetup.setUpPublishableDraftRelease(self.c1)
        release.validate_publishable()
        release.publish()
        self.assertEqual(self.c1.latest_version, release)
        self.assertEqual(
            CodebaseRelease.objects.get(
                codebase=self.c1, version_number=release.version_number
            ),
            release,
        )
        fs_api = release.get_fs_api()
        # check that at least something exists for code/docs
        sip_contents = fs_api.list_sip_contents()
        contents = {
            item["label"]: item.get("contents", []) for item in sip_contents["contents"]
        }
        for category in ["code", "docs"]:
            self.assertIn(category, contents)
            self.assertTrue(contents[category])

    def test_new_draft_carries_forward_data_urls(self):
        source_release = ReleaseSetup.setUpPublishableDraftRelease(self.c1)
        source_release.input_data_url = "https://example.com/input-data"
        source_release.output_data_url = "https://example.com/output-data"
        source_release.save()
        source_release.publish()

        draft_release = self.c1.get_or_create_draft()

        self.assertEqual(draft_release.input_data_url, source_release.input_data_url)
        self.assertEqual(draft_release.output_data_url, source_release.output_data_url)

    def test_new_draft_attributes_submitter_override_not_codebase_submitter(self):
        # the codebase submitter (self.c1.submitter) is self.user, but a different
        # authorized user (e.g. a contributor/curator) may create a subsequent release
        source_release = ReleaseSetup.setUpPublishableDraftRelease(self.c1)
        source_release.publish()
        other_user = UserFactory().create()

        draft_release = self.c1.get_or_create_draft(submitter=other_user)

        self.assertEqual(draft_release.submitter, other_user)
        self.assertNotEqual(self.c1.submitter, other_user)

    def test_publish_syncs_release_submitter_to_discourse(self):
        release = ReleaseSetup.setUpPublishableDraftRelease(self.c1)
        with patch(
            "library.tasks.sync_release_submitter_to_discourse"
        ) as mock_sync_task:
            release.publish()
        mock_sync_task.assert_called_once_with(release.id)

    def test_format_doi_url_rejects_malformed_doi(self):
        invalid_dois = [
            "javascript:alert(1)",
            "https://evil.example/10.1234/test",
            "10.1234/test?next=https://evil.example",
            "10.1234/test#fragment",
            "10.1234/test<script>",
        ]

        for doi in invalid_dois:
            with self.subTest(doi=doi):
                self.assertEqual(Codebase.format_doi_url(doi), "")

    def test_format_doi_url_accepts_datacite_prefixed_doi(self):
        doi = f"{settings.DATACITE_PREFIX}/abc.DEF-123"
        self.assertEqual(
            Codebase.format_doi_url(doi),
            f"https://doi.org/{doi}",
        )

    def test_create_review_draft_from_release(self):
        source_release = ReleaseSetup.setUpPublishableDraftRelease(self.c1)
        source_release.refresh_from_db()
        source_release.publish()
        source_sip_contents = source_release.get_fs_api().list_sip_contents()
        review_draft = self.c1.create_review_draft_from_release(source_release)
        # check metadata
        self.assertEqual(
            review_draft.release_notes.rendered, source_release.release_notes.rendered
        )
        self.assertEqual(review_draft.os, source_release.os)
        self.assertEqual(review_draft.output_data_url, source_release.output_data_url)
        self.assertEqual(review_draft.license, source_release.license)
        self.assertEqual(
            set(review_draft.contributors.all()), set(source_release.contributors.all())
        )
        self.assertEqual(
            set(review_draft.platform_tags.all()),
            set(source_release.platform_tags.all()),
        )
        self.assertEqual(
            set(review_draft.release_languages.all()),
            set(source_release.release_languages.all()),
        )
        self.assertEqual(
            set(ReleaseSetup.PROGRAMMING_LANGUAGES),
            set(source_release.programming_languages.values_list("name", flat=True)),
        )
        self.assertEqual(
            set(ReleaseSetup.PROGRAMMING_LANGUAGES),
            set(review_draft.programming_languages.values_list("name", flat=True)),
        )

        self.assertIsNotNone(source_release.codemeta_snapshot)
        self.assertIsNotNone(source_release.codemeta)

        # check file contents
        draft_sip_contents = review_draft.get_fs_api().list_sip_contents()
        logger.info("source sip contents: %s", source_sip_contents)
        logger.info("draft sip contents: %s", draft_sip_contents)
        # FIXME: basic assertEqual won't work for a newly created review draft
        # from a published release which generates a LICENSE, CITATION.cff, and codemeta.json
        # self.assertEqual(source_sip_contents, review_draft_sip_contents)


class CodebaseReleaseTest(BaseModelTestCase):
    def get_perm_str(self, perm_prefix):
        return "{}.{}_{}".format(
            CodebaseRelease._meta.app_label,
            perm_prefix,
            CodebaseRelease._meta.model_name,
        )

    def setUp(self):
        self.user_factory = UserFactory()
        self.submitter = self.user_factory.create()
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = codebase_factory.create()
        self.codebase_release = self.codebase.create_release(initialize=False)

    def test_anonymous_user_perms(self):
        anonymous_user = AnonymousUser()
        self.assertFalse(anonymous_user.has_perm(self.get_perm_str("add")))
        self.assertFalse(
            anonymous_user.has_perm(
                self.get_perm_str("change"), obj=self.codebase_release
            )
        )
        self.assertFalse(
            anonymous_user.has_perm(
                self.get_perm_str("delete"), obj=self.codebase_release
            )
        )
        self.assertFalse(
            anonymous_user.has_perm(
                self.get_perm_str("view"), obj=self.codebase_release
            )
        )
        self.codebase_release.status = CodebaseRelease.Status.PUBLISHED
        self.codebase_release.save()
        self.assertTrue(
            anonymous_user.has_perm(
                self.get_perm_str("view"), obj=self.codebase_release
            )
        )

    def test_submitter_perms(self):
        submitter = self.submitter
        self.assertTrue(
            submitter.has_perm(self.get_perm_str("change"), obj=self.codebase_release)
        )
        self.assertTrue(
            submitter.has_perm(self.get_perm_str("delete"), obj=self.codebase_release)
        )
        self.assertTrue(
            submitter.has_perm(self.get_perm_str("view"), obj=self.codebase_release)
        )

    def test_superuser_perms(self):
        superuser = self.user_factory.create(is_superuser=True)
        self.assertTrue(superuser.has_perm(self.get_perm_str("add")))
        self.assertTrue(
            superuser.has_perm(self.get_perm_str("change"), obj=self.codebase_release)
        )
        self.assertTrue(
            superuser.has_perm(self.get_perm_str("delete"), obj=self.codebase_release)
        )
        self.assertTrue(
            superuser.has_perm(self.get_perm_str("view"), obj=self.codebase_release)
        )

    def test_regular_user_perms(self):
        regular_user = self.user_factory.create()
        self.assertTrue(regular_user.has_perm(self.get_perm_str("add")))
        self.assertFalse(
            regular_user.has_perm(
                self.get_perm_str("change"), obj=self.codebase_release
            )
        )
        self.assertFalse(
            regular_user.has_perm(
                self.get_perm_str("delete"), obj=self.codebase_release
            )
        )
        self.assertFalse(
            regular_user.has_perm(self.get_perm_str("view"), obj=self.codebase_release)
        )
        self.codebase_release.status = CodebaseRelease.Status.PUBLISHED
        self.codebase_release.save()
        self.assertTrue(
            regular_user.has_perm(self.get_perm_str("view"), obj=self.codebase_release)
        )

    def test_version_number_mutation(self):
        other_codebase_release = self.codebase.create_release(initialize=False)
        version_numbers = other_codebase_release.get_allowed_version_numbers()
        self.assertEqual(
            version_numbers,
            set([semver.parse_version_info(vn) for vn in {"1.0.1", "1.1.0", "2.0.0"}]),
        )

        with self.assertRaises(ValidationError):
            other_codebase_release.set_version_number("1.0.0")

        with self.assertRaises(ValidationError):
            other_codebase_release.set_version_number("foo-1.0.0")

        other_codebase_release.set_version_number("54.2.0")
        self.assertEqual(other_codebase_release.version_number, "54.2.0")

        other_codebase_release.set_version_number("1.0.1")
        self.assertEqual(other_codebase_release.version_number, "1.0.1")

    def test_create_codebase_release_share_uuid(self):
        """Ensure we can create a second codebase release and it has a different share uuid"""
        self.codebase_release.share_uuid = uuid.uuid4()
        self.codebase_release.save()
        cr = self.codebase.create_release(initialize=False)
        self.assertNotEqual(self.codebase_release.share_uuid, cr.share_uuid)

    def test_citation_author_ordering(self):
        release_contributor_factory = ReleaseContributorFactory(self.codebase_release)
        contributor_factory = ContributorFactory(user=self.submitter)
        release_contributors = []
        for contributor in contributor_factory.create_unique_contributors(10):
            # create a release contributor with the same index as the contributor
            # to ensure that the ordering is correct
            release_contributors.append(
                release_contributor_factory.create(contributor, randomize_role=True)
            )
            logger.debug(
                "XXX: created release contributor [%s] with roles: %s",
                release_contributors[-1].contributor,
                release_contributors[-1].roles,
            )
        # check that ordering is correct
        for crc, rc in zip(
            self.codebase_release.citable_release_contributors, release_contributors
        ):
            self.assertEqual(crc.contributor, rc.contributor)
            self.assertEqual(crc.index, rc.index)
            self.assertEqual(crc.roles, rc.roles)

    def test_metadata_completeness(self):
        # make sure release contributors are empty since we currently automatically add the submitter as an author
        self.codebase_release.contributors.all().delete()
        self.assertFalse(self.codebase_release.contributors.exists())

        self.assertRaises(
            ValidationError, lambda: self.codebase_release.validate_publishable()
        )
        self.codebase_release.os = "Windows"
        self.assertRaises(
            ValidationError, lambda: self.codebase_release.validate_publishable()
        )

        license = License.objects.create(
            name="0BSD", url="https://spdx.org/licenses/0BSD.html"
        )
        self.codebase_release.license = license
        self.assertRaises(
            ValidationError, lambda: self.codebase_release.validate_publishable()
        )

        java, _created = ProgrammingLanguage.objects.get_or_create(name="Java")
        ReleaseLanguage.objects.create(
            programming_language=java,
            release=self.codebase_release,
            version="8",
        )
        self.assertRaises(
            ValidationError, lambda: self.codebase_release.validate_publishable()
        )

        release_contributor_factory = ReleaseContributorFactory(self.codebase_release)
        contributor_factory = ContributorFactory(user=self.submitter)
        contributor = contributor_factory.create()
        release_contributor_factory.create(contributor)

        self.assertRaises(
            ValidationError, lambda: self.codebase_release.validate_publishable()
        )
        self.assertTrue(self.codebase_release.validate_metadata())
