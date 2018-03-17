import logging

from django import forms
from django.conf import settings
from django.core.mail import EmailMessage
from django.template import loader
from django.utils.translation import ugettext_lazy as _
from wagtail.core.models import Site

from core.models import SocialMediaSettings

logger = logging.getLogger(__name__)


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, label=_('Your name'))
    email = forms.EmailField(max_length=255, label=_('Your email address'))
    subject_text = forms.CharField(max_length=100, label=_('Message subject'))
    body = forms.CharField(widget=forms.Textarea, label=_('Your message'))

    subject_template_name = 'home/about/contact_form_subject.txt'
    template_name = 'home/about/contact_form_email.txt'
    from_email = settings.DEFAULT_FROM_EMAIL

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
        recipients = SocialMediaSettings.for_site(self.request.site).contact_form_recipients
        if not recipients:
            recipients = ('editors@comses.net',)
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
        email = EmailMessage(
            subject=self.subject,
            body=self.message,
            to=self.recipient_list,
            reply_to=[self.cleaned_data.get('email') or self.from_email],
        )
        email.send(fail_silently=fail_silently)
