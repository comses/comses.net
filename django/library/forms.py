import logging

from django import forms

from core.models import MemberProfile
from .models import PeerReview, PeerReviewerFeedback, PeerReviewInvitation, PeerReviewEventLog

logger = logging.getLogger(__name__)


class PeerReviewEditForm(forms.ModelForm):
    def save(self, commit=True):
        review = self.instance.editor_change_review_status(self.cleaned_data['status'])
        return review

    class Meta:
        model = PeerReview
        fields = ['status',]


class PeerReviewInvitationForm(forms.ModelForm):
    def save(self, commit=True):
        invitation = super().save(commit)
        invitation.send_email()
        return invitation

    class Meta:
        model = PeerReviewInvitation
        fields = [
            'review',
            'editor',
            'candidate_reviewer',
            'candidate_email',
        ]


class PeerReviewInvitationReplyForm(forms.ModelForm):
    def clean_accepted(self):
        data = self.cleaned_data['accepted']
        if data is None:
            raise forms.ValidationError('Must accept or decline invitation')
        return data

    def save(self, commit=True):
        accepted = self.instance.accepted
        invitation = super().save(commit)

        if invitation.accepted:
            invitation.accept_invitation()
        else:
            invitation.declined_invitation()

        if invitation.accepted and accepted is None:
            invitation.create_feedback()
        return invitation

    class Meta:
        model = PeerReviewInvitation
        fields = ['accepted']


class CheckCharFieldLengthMixin:
    def _check_char_field_has_content(self, field_name, min_length=10):
        content = self.cleaned_data[field_name]
        if len(content) < min_length:
            raise forms.ValidationError('Field {} must have at least {} characters'.format(
                PeerReviewerFeedback._meta.get_field(field_name).verbose_name, min_length))
        return content


class PeerReviewerFeedbackReviewerForm(CheckCharFieldLengthMixin, forms.ModelForm):
    def clean_recommendation(self):
        recommendation = self.cleaned_data['recommendation']
        if not recommendation:
            raise forms.ValidationError('Recommendation must be selected')
        return recommendation

    def clean_private_reviewer_notes(self):
        return self._check_char_field_has_content(field_name='private_reviewer_notes')

    def clean_narrative_documentation_comments(self):
        return self._check_char_field_has_content(field_name='narrative_documentation_comments')

    def clean_clean_code_comments(self):
        return self._check_char_field_has_content(field_name='clean_code_comments')

    def clean_runnable_comments(self):
        return self._check_char_field_has_content(field_name='runnable_comments')

    def save(self, commit=True):
        feedback = super().save(commit)
        feedback.reviewer_gave_feedback()
        return feedback

    class Meta:
        model = PeerReviewerFeedback
        fields = ['recommendation',
                  'private_reviewer_notes',
                  'has_narrative_documentation',
                  'narrative_documentation_comments',
                  'has_clean_code',
                  'clean_code_comments',
                  'is_runnable',
                  'runnable_comments']


class PeerReviewerFeedbackEditorForm(CheckCharFieldLengthMixin, forms.ModelForm):
    def clean_notes_to_author(self):
        return self._check_char_field_has_content('notes_to_author')

    def save(self, commit=True):
        feedback = super().save(commit)
        feedback.editor_called_for_revisions()
        return feedback

    class Meta:
        model = PeerReviewerFeedback
        fields = [
            'private_editor_notes',
            'notes_to_author'
        ]
