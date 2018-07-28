import re

from django import forms

from conference.models import Submission2018


YOUTUBE_URL = re.compile(r'^https?://(www\.)?youtube.com(.*)')


class Submission2018Form(forms.ModelForm):
    def clean_video_url(self):
        video_url = self.cleaned_data['video_url']
        if not re.match(YOUTUBE_URL, video_url):
            raise forms.ValidationError('Video URL must be a Youtube URL')
        return video_url

    class Meta:
        model = Submission2018
        fields = ('id', 'title', 'abstract', 'video_url', 'release_url', 'author')
        widgets = {
            'author': forms.HiddenInput()
        }

