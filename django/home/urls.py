from django.conf.urls import url, include
from django.views.generic import TemplateView
from . import views
from . import models
from .forms import RegistrationForm
from rest_framework.routers import SimpleRouter
from core.view_helpers import create_edit_routes
from registration.backends.hmac.views import RegistrationView

router = SimpleRouter()
router.register(r'events', views.EventViewSet, base_name='event')
router.register(r'jobs', views.JobViewSet, base_name='job')
router.register(r'tags', views.TagViewSet, base_name='tag')

urlpatterns = []
edit_route_form_data = {'lookup_field': 'pk', 'lookup_regex': r'\d+'}
for model in [models.Job, models.Event]:
    urlpatterns += create_edit_routes(prefix=model._meta.object_name.lower() + 's', model=model, **edit_route_form_data)

urlpatterns += [
    url(r'^$', TemplateView.as_view(template_name='home/index.jinja'), name='index'),
    url(r'^', include(router.urls)),
    url(r'^resources/$', TemplateView.as_view(template_name='home/resources.jinja'),
        name='resources'),
    url(r'^community/$', TemplateView.as_view(template_name='home/community.jinja'), name='community'),
    # account URLs
    url(r'^accounts/membership/', TemplateView.as_view(template_name='registration/membership.html'),
        name='membership'),
    url(r'^accounts/register/', RegistrationView.as_view(form_class=RegistrationForm),
        name='register'),
    url(r'^accounts/profile/', TemplateView.as_view(template_name='accounts/profile.jinja'),
        name='profile'),
]

urlpatterns += router.urls
