import logging

from django import forms
from django.forms.utils import ErrorDict
from django.utils.translation import ugettext_lazy as _

from .models import PeerReviewerFeedback, PeerReviewInvitation, ReviewerRecommendation

logger = logging.getLogger(__name__)


class PeerReviewInvitationForm(forms.ModelForm):
    """
    Sends an invitation to a candidate reviewer
    """
    def save(self, commit=True):
        invitation = super().save(commit)
        invitation.send_candidate_reviewer_email()
        return invitation

    class Meta:
        model = PeerReviewInvitation
        fields = [
            'review',
            'editor',
            'candidate_reviewer',
        ]


class PeerReviewInvitationReplyForm(forms.ModelForm):
    """
    Processes a peer review invitation reply (accept / decline) from a candidate reviewer
    """
    def clean_accepted(self):
        data = self.cleaned_data['accepted']
        if data is None:
            raise forms.ValidationError('Please accept or decline the invitation')
        return data

    def save(self, commit=True):
        invitation = super().save(commit=commit)
        if invitation.accepted:
            invitation.accept()
        else:
            invitation.decline()
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
            raise forms.ValidationError('Please select a valid recommendation (accept or revise).')
        return recommendation

    def clean_narrative_documentation_comments(self):
        return self._check_char_field_has_content(field_name='narrative_documentation_comments')

    def clean_clean_code_comments(self):
        return self._check_char_field_has_content(field_name='clean_code_comments')

    def clean_runnable_comments(self):
        return self._check_char_field_has_content(field_name='runnable_comments')

    def clean(self):
        cleaned_data = super().clean()
        reviewer_submitted = cleaned_data.get('reviewer_submitted')
        if reviewer_submitted and cleaned_data.get('recommendation') == ReviewerRecommendation.accept.name:
            has_narrative_documentation = cleaned_data['has_narrative_documentation']
            has_clean_code = cleaned_data['has_clean_code']
            is_runnable = cleaned_data['is_runnable']

            checklist_errors = []

            if is_runnable:
                self.fields_required(['runnable_comments'])
                checklist_errors.append(_('Recommended releases must have runnable code.'))
            else:
                self.cleaned_data['runnable_comments'] = ''

            if has_narrative_documentation:
                self.fields_required(['narrative_documentation_comments'])
            else:
                self.cleaned_data['narrative_documentation_comments'] = ''
                checklist_errors.append(_('Recommended releases must have accompanying narrative documentation.'))

            if has_clean_code:
                self.fields_required(['clean_code_comments'])
            else:
                self.cleaned_data['clean_code_comments'] = ''
                checklist_errors.append(_('Recommended releases should have clean code.'))

            if checklist_errors:
                raise forms.ValidationError([forms.ValidationError(e) for e in checklist_errors])

        return cleaned_data

    def full_clean(self):
        self._errors = ErrorDict()
        if not self.is_bound:  # Stop further processing.
            return
        self.cleaned_data = {}
        # If the form is permitted to be empty, and none of the form data has
        # changed from the initial data, short circuit any validation.
        if self.empty_permitted and not self.has_changed():
            return

        self._clean_fields()
        if not self.cleaned_data.get('reviewer_submitted', True):
            self._errors = ErrorDict()
        if self.instance.invitation.review.is_complete:
            self.add_error(field=None, error='Feedback cannot be updated on a completed review')
        # FIXME: we should not rely on internal marked methods, need to clean this up
        self._clean_form()
        self._post_clean()

    """ Mark conditional fields required """
    def fields_required(self, fields):
        for field in fields:
            if not self.cleaned_data.get(field, ''):
                msg = forms.ValidationError("This field is required")
                self.add_error(field, msg)

    def save(self, commit=True):
        feedback = super().save(commit)
        if feedback.reviewer_submitted:
            feedback.reviewer_completed()
        return feedback

    class Meta:
        model = PeerReviewerFeedback
        fields = [
            'is_runnable',
            'runnable_comments',
            'has_narrative_documentation',
            'narrative_documentation_comments',
            'has_clean_code',
            'clean_code_comments',
            'private_reviewer_notes',
            'reviewer_submitted',
            'recommendation',
        ]
        widgets = {
            'reviewer_submitted': forms.HiddenInput()
        }


class PeerReviewerFeedbackEditorForm(CheckCharFieldLengthMixin, forms.ModelForm):
    def __init__(self, **kwargs):
        if 'instance' in kwargs:
            feedback = kwargs['instance']
            kwargs['initial']['accept'] = feedback.invitation.review.is_complete
        super().__init__(**kwargs)

    accept = forms.BooleanField(label='Accept?', required=False)

    def clean_notes_to_author(self):
        return self._check_char_field_has_content('notes_to_author')

    def save(self, commit=True):
        feedback = super().save(commit)
        if self.cleaned_data['accept']:
            feedback.invitation.review.set_complete_status(editor=feedback.invitation.editor)
        else:
            feedback.editor_called_for_revisions()
        return feedback

    class Meta:
        model = PeerReviewerFeedback
        fields = [
            'private_editor_notes',
            'notes_to_author',
            'accept'
        ]
