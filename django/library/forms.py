from django import forms

from core import models
from .models import PeerReview, PeerReviewerFeedback, PeerReviewInvitation


class PeerReviewEditForm(forms.ModelForm):
    class Meta:
        model = PeerReview
        fields = ['status',]


class PeerReviewInvitationForm(forms.ModelForm):
    class Meta:
        model = PeerReviewInvitation
        fields = [
            'review',
            'editor',
            'candidate_reviewer',
            'candidate_email',
        ]


class PeerReviewInvitationReplyForm(forms.Form):
    email = forms.EmailField()
    review_url = forms.URLField()
    message = forms.CharField(widget=forms.Textarea)


class PeerReviewerFeedbackReviewerForm(forms.ModelForm):
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


class PeerReviewerFeedbackEditorForm(forms.ModelForm):
    class Meta:
        model = PeerReviewerFeedback
        fields = [
            'private_editor_notes',
            'notes_to_author'
        ]


