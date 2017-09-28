from django.conf.urls import url
from rest_framework.routers import SimpleRouter
from django.views.generic import TemplateView

from core.models import Event, Job, MemberProfile
from core.routers import AddEditRouter
from . import views

add_edit_router = AddEditRouter()

router = SimpleRouter()
router.register(r'tags', views.TagViewSet, base_name='tag')
router.register(r'events', views.EventViewSet, base_name='event')
router.register(r'jobs', views.JobViewSet, base_name='job')
router.register(r'users', views.ProfileViewSet, base_name='profile')

urlpatterns = [
    url(r'^discourse/sso$', views.discourse_sso, name='discourse-sso'),
    url(r'^users/follow/$', views.ToggleFollowUser.as_view(), name='follow-user'),
    url(r'^events/calendar/$', views.EventCalendarList.as_view(), name='event-calendar'),
    url(r'^events/(?P<pk>\d+)/edit/$', views.EventUpdateView.as_view(), name='event-edit'),
    url(r'^events/add/$', views.EventCreateView.as_view(), name='event-add'),
    url(r'^jobs/(?P<pk>\d+)/edit/$', views.JobUpdateView.as_view(), name='job-edit'),
    url(r'^jobs/add/$', views.JobCreateView.as_view(), name='job-add'),
    url(r'^users/(?P<username>[\w\.\-@]+)/edit/$', views.ProfileUpdateView.as_view(), name='profile-edit'),
]

urlpatterns.append(url(r'users/(?P<username>(\w+))/upload_picture/$', views.MemberProfileImageUploadView.as_view()))

urlpatterns += add_edit_router.urls
urlpatterns += router.urls
