from django.conf.urls import url
from rest_framework.routers import SimpleRouter
from guardian.decorators import permission_required_or_403
from django.views.generic import TemplateView

from core.models import Event, Job, MemberProfile
from core.view_helpers import create_edit_routes
from . import views

router = SimpleRouter()
router.register(r'events', views.EventViewSet, base_name='event')
router.register(r'jobs', views.JobViewSet, base_name='job')
router.register(r'tags', views.TagViewSet, base_name='tag')
router.register(r'users', views.ProfileViewSet, base_name='profile')

urlpatterns = [
    url(r'^discourse/sso$', views.discourse_sso, name='discourse-sso'),
    url(r'^users/follow/$', views.ToggleFollowUser.as_view(), name='follow-user'),
    url(r'^events/calendar/$', views.EventCalendarList.as_view(), name='events-calendar')
]

urlpatterns.append(url(r'^users/(?P<username>(\w+))/update/$',
                       permission_required_or_403(
                           'core.change_memberprofile', (MemberProfile, 'user__username', 'username'))(
                           TemplateView.as_view(template_name='home/profiles/update.jinja')), name='profile-update'))
urlpatterns.append(url(r'users/(?P<username>(\w+))/update/picture/$', views.MemberProfileImageUploadView.as_view()))

edit_route_form_data = {'lookup_field': 'pk', 'lookup_regex': r'\d+'}
# FIXME: see https://github.com/comses/core.comses.net/issues/70 - these urls must come before router.urls
for model in (Event, Job):
    urlpatterns += create_edit_routes(prefix=model._meta.object_name.lower() + 's', model=model, **edit_route_form_data)

urlpatterns += router.urls
