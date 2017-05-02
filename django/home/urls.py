import itertools

from django.conf.urls import url
from rest_framework.routers import SimpleRouter

from core.view_helpers import create_edit_routes
from . import models, views

router = SimpleRouter()
router.register(r'events', views.EventViewSet, base_name='event')
router.register(r'jobs', views.JobViewSet, base_name='job')
router.register(r'tags', views.TagViewSet, base_name='tag')
router.register(r'users', views.ProfileViewSet, base_name='profile')
router.register(r'calendar_events', views.EventCalendarList, base_name='calendar_event')

urlpatterns = [
    url(r'^discourse/sso$', views.discourse_sso, name='discourse_sso'),
]
edit_route_form_data = {'lookup_field': 'pk', 'lookup_regex': r'\d+'}
# FIXME: see https://github.com/comses/core.comses.net/issues/70 - these urls must come before router.urls
for model in [models.Job, models.Event]:
    urlpatterns += create_edit_routes(prefix=model._meta.object_name.lower() + 's', model=model, **edit_route_form_data)

urlpatterns += router.urls
