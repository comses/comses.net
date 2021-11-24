import logging

from hcaptcha_field import hCaptchaField
from django import forms
from django.utils.translation import ugettext_lazy as _

from .models import ComsesGroups

logger = logging.getLogger(__name__)


class SignupForm(forms.Form):
    error_css_class = 'has-errors'
    required_css_class = 'required'
    field_order = ('username', 'email', 'first_name', 'last_name', 'full_member', 'password1', 'password2', 'captcha')

    username = forms.CharField(max_length=200, strip=True, required=True)
    email = forms.EmailField(max_length=200, required=True)
    first_name = forms.CharField(max_length=200, strip=True, required=False, label='Given name')
    last_name = forms.CharField(max_length=200, strip=True, required=False, label='Family name')
    full_member = forms.BooleanField(
        required=False,
        help_text=_("By checking this box, I agree to the rights and responsibilities of CoMSES Net full membership")
    )
    captcha = hCaptchaField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def signup(self, request, user):
        data = self.cleaned_data
        user.username = data['username'].lower()
        user.email = data['email'].lower()
        user.first_name = data.get('first_name')
        user.last_name = data.get('last_name')
        password = data.get('password1')
        if password and password == data.get('password2'):
            user.set_password(password)
        else:
            user.set_unusable_password()
        full_member = data.get('full_member')
        if full_member:
            user.groups.add(ComsesGroups.FULL_MEMBER.get_group())
            # FIXME: add user to mailchimp list
        user.save()
