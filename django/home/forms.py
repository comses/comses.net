import logging

from django import forms
from django.utils.translation import ugettext_lazy as _

from .models import ComsesGroups

logger = logging.getLogger(__name__)


class SignupForm(forms.Form):
    error_css_class = 'has-errors'
    required_css_class = 'required'

    username = forms.CharField(max_length=200, strip=True, required=True)
    email = forms.EmailField(max_length=200, required=True)
    first_name = forms.CharField(max_length=200, strip=True, required=False,
                                 label='Given name')
    last_name = forms.CharField(max_length=200, strip=True, required=False,
                                label='Family name')
    full_member = forms.BooleanField(
        required=False,
        help_text=_("By checking this box, I agree to the rights and responsibilities of CoMSES Net full membership"))

    def signup(self, request, user):
        data = self.cleaned_data
        user.username = data['username']
        user.email = data['email']
        user.first_name = data['first_name']
        user.last_name = data['last_name']
        password = data['password1']
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        full_member = data['full_member']
        if full_member:
            user.groups.add(ComsesGroups.FULL_MEMBER.get_group())
        logger.error("about to save USER %s", user)
        user.save()

