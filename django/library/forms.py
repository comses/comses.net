import logging

from django import forms

from .models import PeerReview, PeerReviewerFeedback, PeerReviewInvitation

logger = logging.getLogger(__name__)


class PeerReviewEditForm(forms.ModelForm):
    class Meta:
        model = PeerReview
        fields = ['status', ]


class PeerReviewInvitationForm(forms.ModelForm):
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
        instance = super().save(commit)
        if instance.accepted:
            instance.create_feedback()
        return instance

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

    class Meta:
        model = PeerReviewerFeedback
        fields = [
            'private_editor_notes',
            'notes_to_author'
        ]
