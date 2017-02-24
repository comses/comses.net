from django.conf.urls import url, include
from django.views.generic import TemplateView
from .forms import RegistrationForm
from registration.backends.hmac.views import RegistrationView


urlpatterns = [
    # also pulls in urls from
    # https://github.com/ubernostrum/django-registration/blob/master/registration/auth_urls.py
    url(r'^accounts/', include('registration.backends.hmac.urls')),
    url(r'^accounts/register/', RegistrationView.as_view(form_class=RegistrationForm),
        name='register'),
    url(r'^accounts/profile/', TemplateView.as_view(template_name='accounts/profile.jinja'), 
        name='profile'),
]
