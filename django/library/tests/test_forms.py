from django import forms
from django.test import TestCase

from library.forms import PeerReviewerFeedbackReviewerForm
from .base import ReviewSetup


class PeerReviewerFeedbackFormTestCase(ReviewSetup, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.setUpReviewData()

    def test_cannot_recommend_if_code_is_not_clean(self):
        invitation = self.review.invitation_set.create(editor=self.editor,
                                                    candidate_reviewer=self.reviewer)
        feedback = invitation.create_feedback()

        # Submitted changes should be validated
        data = PeerReviewerFeedbackReviewerForm(instance=feedback).initial.copy()
        data['recommendation'] = 'accept'
        data['reviewer_submitted'] = True
        form = PeerReviewerFeedbackReviewerForm(data, instance=feedback)
        with self.assertRaises(forms.ValidationError):
            form.is_valid()
            if form.errors:
                raise forms.ValidationError(form.errors)

        # Unsubmitted feedback should not undergo validation
        data['reviewer_submitted'] = False
        form = PeerReviewerFeedbackReviewerForm(data, instance=feedback)
        form.is_valid()
        if form.errors:
            raise forms.ValidationError(form.errors)