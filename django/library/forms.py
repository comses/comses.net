from django import forms

from .models import PeerReview


class PeerReviewEditorForm(forms.ModelForm):

    class Meta:
        model = PeerReview
        fields = ['status', 'codebase_release',]


class PeerReviewInvitationForm(forms.Form):
    email = forms.EmailField()
    review_url = forms.URLField()
    message = forms.CharField(widget=forms.Textarea)
