from registration.forms import RegistrationForm as DjangoRegistrationForm
from django.forms import fields


class RegistrationForm(DjangoRegistrationForm):
    institution = fields.CharField(max_length=200, strip=True, required=False)
    full_member = fields.BooleanField(required=False)
