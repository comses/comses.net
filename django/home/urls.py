from django.conf.urls import url
from rest_framework.routers import SimpleRouter

import core.views
from core.routers import AddEditRouter
from . import views

add_edit_router = AddEditRouter()

router = SimpleRouter()
router.register(r'tags', views.TagListView, base_name='tag')
router.register(r'events', core.views.EventViewSet, base_name='event')
router.register(r'jobs', core.views.JobViewSet, base_name='job')
router.register(r'users', views.ProfileViewSet, base_name='profile')

urlpatterns = [
    url(r'^users/follow/$', views.ToggleFollowUser.as_view(), name='follow-user'),
    url(r'^events/calendar/$', core.views.EventCalendarList.as_view(), name='event-calendar'),
    url(r'^events/(?P<pk>\d+)/edit/$', views.EventUpdateView.as_view(), name='event-edit'),
    url(r'^events/add/$', views.EventCreateView.as_view(), name='event-add'),
    url(r'^jobs/(?P<pk>\d+)/edit/$', views.JobUpdateView.as_view(), name='job-edit'),
    url(r'^jobs/add/$', views.JobCreateView.as_view(), name='job-add'),
    url(r'^about/contact/sent/$', views.ContactSentView.as_view(template_name='home/about/contact-sent.jinja'), name='contact-sent'),
    url(r'^users/(?P<username>[\w\.\-@]+)/edit/$', views.ProfileUpdateView.as_view(), name='profile-edit'),
    url(r'^accounts/profile/$', views.ProfileRedirectView.as_view(), name='account-profile'),
]

urlpatterns.append(url(r'users/(?P<username>(\w+))/upload_picture/$', views.MemberProfileImageUploadView.as_view()))

urlpatterns += add_edit_router.urls
urlpatterns += router.urls
