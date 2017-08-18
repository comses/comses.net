from django.conf.urls import url
from rest_framework.routers import SimpleRouter
from guardian.decorators import permission_required_or_403
from django.views.generic import TemplateView

from core.models import Event, Job, MemberProfile
from core.routers import AddEditRouter
from . import views

add_edit_router = AddEditRouter()
add_edit_router.register(r'events', views.EventViewSet, base_name='event')
add_edit_router.register(r'jobs', views.JobViewSet, base_name='job')
add_edit_router.register(r'users', views.ProfileViewSet, base_name='profile')

router = SimpleRouter()
router.register(r'tags', views.TagViewSet, base_name='tag')

urlpatterns = [
    url(r'^discourse/sso$', views.discourse_sso, name='discourse-sso'),
    url(r'^users/follow/$', views.ToggleFollowUser.as_view(), name='follow-user'),
    url(r'^events/calendar/$', views.EventCalendarList.as_view(), name='events-calendar')
]

urlpatterns.append(url(r'^users/(?P<username>(\w+))/update/$',
                       permission_required_or_403(
                           'core.change_memberprofile', (MemberProfile, 'user__username', 'username'))(
                           TemplateView.as_view(template_name='home/profiles/update.jinja')), name='profile-update'))
urlpatterns.append(url(r'users/(?P<username>(\w+))/edit/picture/$', views.MemberProfileImageUploadView.as_view()))

urlpatterns += add_edit_router.urls
urlpatterns += router.urls
