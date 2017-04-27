import logging

from django import forms

from .models import Institution, ComsesGroups

logger = logging.getLogger(__name__)


class SignupForm(forms.Form):
    username = forms.CharField(max_length=200, strip=True, required=True)
    email = forms.EmailField(max_length=200, strip=True, required=True)
    first_name = forms.CharField(max_length=200, strip=True, required=False)
    last_name = forms.CharField(max_length=200, strip=True, required=False)
    institution = forms.CharField(max_length=200, strip=True, required=False)
    full_member = forms.BooleanField(required=False)

    def signup(self, request, user):
        data = self.cleaned_data
        user.username = data['username']
        user.email = data['email']
        user.first_name = data.get('first_name')
        user.last_name = data.get('last_name')
        password = data.get('password1')
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        # save basic member profile information
        institution_name = data.get('institution')
        if institution_name:
            institution = Institution.objects.get_or_create(name=institution_name)
            user.member_profile.institution = institution
        full_member = data['full_member']
        if full_member:
            user.groups.add(ComsesGroups.FULL_MEMBER.get_group())
        user.member_profile.save()
