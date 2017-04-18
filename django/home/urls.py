from django.conf.urls import url, include
from django.views.generic import TemplateView
from rest_framework.routers import SimpleRouter

from core.view_helpers import create_edit_routes
from . import models, views

router = SimpleRouter()
router.register(r'events', views.EventViewSet, base_name='event')
router.register(r'jobs', views.JobViewSet, base_name='job')
router.register(r'tags', views.TagViewSet, base_name='tag')
router.register(r'users', views.ProfileViewSet, base_name='profile')

urlpatterns = router.urls
edit_route_form_data = {'lookup_field': 'pk', 'lookup_regex': r'\d+'}
for model in [models.Job, models.Event]:
    urlpatterns += create_edit_routes(prefix=model._meta.object_name.lower() + 's', model=model, **edit_route_form_data)

urlpatterns += [
    url(r'^discourse/sso$', views.discourse_sso, name='discourse_sso'),
]
