from django.conf.urls import url
from django.views.generic import TemplateView
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register(r'tags', views.TagListView, base_name='tag')
router.register(r'events', views.EventViewSet, base_name='event')
router.register(r'jobs', views.JobViewSet, base_name='job')
router.register(r'users', views.ProfileViewSet, base_name='profile')

urlpatterns = [
    url(r'^digest/$', TemplateView.as_view(template_name='home/digest.jinja'), name='digest'),
    url(r'^users/follow/$', views.ToggleFollowUser.as_view(), name='follow-user'),
    url(r'^events/(?P<pk>\d+)/edit/$', views.EventUpdateView.as_view(), name='event-edit'),
    url(r'^events/add/$', views.EventCreateView.as_view(), name='event-add'),
    url(r'^jobs/(?P<pk>\d+)/edit/$', views.JobUpdateView.as_view(), name='job-edit'),
    url(r'^jobs/add/$', views.JobCreateView.as_view(), name='job-add'),
    url(r'^about/contact/sent/$', views.ContactSentView.as_view(), name='contact-sent'),
    url(r'^users/(?P<user__pk>\d+)/edit/$', views.ProfileUpdateView.as_view(), name='profile-edit'),
    url(r'^accounts/profile/$', views.ProfileRedirectView.as_view(), name='account-profile'),
    url(r'users/(?P<user__pk>\d+)/upload_picture/$', views.MemberProfileImageUploadView.as_view(),
        name='profile-avatar-upload'),
] + router.urls
