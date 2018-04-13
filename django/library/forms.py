from django import forms

from .models import PeerReview


class PeerReviewEditorForm(forms.ModelForm):

    class Meta:
        model = PeerReview
        fields = ['status', 'codebase_release', 'private_editor_notes', 'notes_to_author']
