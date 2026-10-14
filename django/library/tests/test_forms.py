from django import forms
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from library.forms import (
    PeerReviewerFeedbackReviewerForm,
    PeerReviewerFeedbackEditorForm,
)
from .base import ReviewSetup


class PeerReviewerFeedbackFormTestCase(ReviewSetup, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.setUpReviewData()

    def test_cannot_recommend_if_code_is_not_clean(self):
        invitation = self.review.invitation_set.create(
            editor=self.editor,
            candidate_reviewer=self.reviewer.member_profile,
            reviewer=self.reviewer,
            accepted=True,
        )
        feedback = invitation.latest_feedback

        # Submitted changes should be validated
        data = PeerReviewerFeedbackReviewerForm(instance=feedback).initial.copy()
        data["recommendation"] = "accept"
        data["reviewer_submitted"] = True
        form = PeerReviewerFeedbackReviewerForm(data, instance=feedback)
        with self.assertRaises(forms.ValidationError):
            form.is_valid()
            if form.errors:
                raise forms.ValidationError(form.errors)

        # Unsubmitted feedback should not undergo validation
        data["reviewer_submitted"] = False
        form = PeerReviewerFeedbackReviewerForm(data, instance=feedback)
        form.is_valid()
        if form.errors:
            raise forms.ValidationError(form.errors)

    def test_cancelled_draft_cannot_be_resurrected_by_a_stale_form(self):
        invitation = self.review.invitation_set.create(
            editor=self.editor,
            candidate_reviewer=self.reviewer.member_profile,
            reviewer=self.reviewer,
            accepted=True,
        )
        feedback = invitation.latest_feedback
        data = PeerReviewerFeedbackReviewerForm(instance=feedback).initial.copy()
        data["reviewer_submitted"] = False
        form = PeerReviewerFeedbackReviewerForm(data, instance=feedback)
        self.assertTrue(form.is_valid())
        self.review.close(self.submitter.member_profile)
        with self.assertRaises(ValidationError):
            form.save()
        self.assertEqual(invitation.feedback_set.count(), 0)

    def test_closed_review_feedback_cannot_be_certified(self):
        invitation = self.review.invitation_set.create(
            editor=self.editor,
            candidate_reviewer=self.reviewer.member_profile,
            reviewer=self.reviewer,
            accepted=True,
        )
        feedback = invitation.feedback_set.create(reviewer_submitted=True)
        type(self.review).objects.filter(pk=self.review.pk).update(closed=True)
        editor_form = PeerReviewerFeedbackEditorForm(
            data={"accept": True, "notes_to_author": "Certification notes"},
            instance=feedback,
            initial={},
            editor=self.editor,
        )
        self.assertFalse(editor_form.is_valid())
        self.assertIn("closed or complete", str(editor_form.errors))
