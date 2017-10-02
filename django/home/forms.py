import logging

from django import forms
from django.conf import settings
from django.core.mail import send_mail
from django.template import loader
from django.utils.translation import ugettext_lazy as _
from wagtail.wagtailcore.models import Site

from core.models import ComsesGroups, SocialMediaSettings

logger = logging.getLogger(__name__)


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, label=_('Your name'))
    email = forms.EmailField(max_length=255, label=_('Your email address'))
    body = forms.CharField(widget=forms.Textarea, label=_('Your message'))

    subject_template_name = 'home/contact/contact_form_subject.txt'
    template_name = 'home/contact/contact_form_email.txt'
    from_email = settings.DEFAULT_FROM_EMAIL

    def __init__(self, data=None, files=None, request=None, *args, **kwargs):
        if request is None:
            raise ValueError("kwarg request is required")
        self.request = request
        super().__init__(data=data, files=files, *args, **kwargs)

    def get_context(self):
        if not self.is_valid():
            raise ValueError("Cannot get_context() from invalid contact form")
        site = Site.objects.first()
        return dict(self.cleaned_data, site=site)

    @property
    def recipient_list(self):
        wagtail_settings = SocialMediaSettings.for_site(self.request.site)
        return wagtail_settings.contact_form_email.split(',')

    @property
    def subject(self):
        subject = loader.render_to_string(
            self.template_name, self.get_context(), request=self.request
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
        message_dict = {
            'from_email': self.from_email,
            'recipient_list': self.recipient_list,
            'subject': self.subject,
            'message': self.message,
        }
        send_mail(fail_silently=fail_silently, **message_dict)



