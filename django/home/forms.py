import logging

from hcaptcha_field import hCaptchaField

from django import forms
from django.conf import settings
from django.template import loader
from django.utils.translation import ugettext_lazy as _
from urllib.parse import urlparse
from wagtail.core.models import Site

from core.models import SocialMediaSettings
from core.utils import send_markdown_email
from .models import ConferenceSubmission

logger = logging.getLogger(__name__)


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, label=_('Your name'))
    email = forms.EmailField(max_length=255, label=_('Your email address'))
    subject_text = forms.CharField(max_length=100, label=_('Message subject'))
    body = forms.CharField(widget=forms.Textarea, label=_('Your message'))

    subject_template_name = 'home/about/contact_form_subject.txt'
    template_name = 'home/about/contact_form_email.txt'
    from_email = settings.DEFAULT_FROM_EMAIL
    captcha = hCaptchaField()

    def __init__(self, request=None, initial=None, *args, **kwargs):
        if request is None:
            raise ValueError("kwarg request is required")
        if initial is None:
            initial = {}
        self.request = request
        if request.user.is_authenticated:
            user = request.user
            initial.update(name=user.member_profile.name,
                           email=user.email)
        super().__init__(initial=initial, *args, **kwargs)

    def get_context(self):
        if not self.is_valid():
            raise ValueError("Cannot get_context() from invalid contact form")
        site = Site.objects.first()
        return dict(self.cleaned_data, site=site)

    @property
    def recipient_list(self):
        recipients = SocialMediaSettings.for_request(self.request).contact_form_recipients
        if not recipients:
            recipients = [settings.EDITOR_EMAIL]
        return recipients

    @property
    def subject(self):
        subject = loader.render_to_string(
            self.subject_template_name, self.get_context(), request=self.request
        )
        return ''.join(subject.splitlines())

    @property
    def message(self):
        """
        Returns the template rendered message body as a string.
        :return:
        """
        return loader.render_to_string(
            self.template_name, self.get_context(), request=self.request
        )

    def save(self, fail_silently=False):
        if not self.is_valid():
            raise ValueError("Can't send a message from invalid contact form")
        from_email = self.cleaned_data.get('email') or self.from_email
        send_markdown_email(
            subject=self.subject,
            template_name=self.template_name,
            context=self.get_context(),
            to=self.recipient_list,
            from_email=from_email,
            reply_to=[from_email],
        )


class ConferenceSubmissionForm(forms.ModelForm):
    def clean_video_url(self):
        video_url = self.cleaned_data['video_url'].strip()
        # This doesn't work for all youtube urls. https://gist.github.com/Glurt/ea11b690ba4b1278e049
        # if not re.match(YOUTUBE_URL, video_url):
        #    raise forms.ValidationError('Video URL must be a Youtube URL')
        domain = urlparse(video_url).netloc
        if domain in ('youtube.com', 'youtu.be'):
            return video_url
        raise forms.ValidationError('Please submit a YouTube URL - it will make our lives much easier organizing the content. Thank you!')

    class Meta:
        model = ConferenceSubmission
        fields = ('id', 'title', 'abstract', 'video_url', 'model_url',)
