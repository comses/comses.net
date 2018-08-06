from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

app_name = 'home'

router = SimpleRouter()
router.register(r'tags', views.TagListView, base_name='tag')
router.register(r'events', views.EventViewSet, base_name='event')
router.register(r'jobs', views.JobViewSet, base_name='job')
router.register(r'users', views.ProfileViewSet, base_name='profile')

# FIXME: replace re_path with https://docs.djangoproject.com/en/2.0/ref/urls/#django.urls.path matching, e.g., <int:pk>

urlpatterns = [
    path('digest/', views.DigestView.as_view(), name='digest'),
    path('conference/submit/', views.ConferenceSubmissionView.as_view(), name='submit-conference'),
    path('users/follow/', views.ToggleFollowUser.as_view(), name='follow-user'),
    path('events/<int:pk>/edit/', views.EventUpdateView.as_view(), name='event-edit'),
    path('events/add/', views.EventCreateView.as_view(), name='event-add'),
    path('jobs/<int:pk>/edit/', views.JobUpdateView.as_view(), name='job-edit'),
    path('jobs/add/', views.JobCreateView.as_view(), name='job-add'),
    path('about/contact/sent/', views.ContactSentView.as_view(), name='contact-sent'),
    path('users/<int:user__pk>/edit/', views.ProfileUpdateView.as_view(), name='profile-edit'),
    path('accounts/profile/', views.ProfileRedirectView.as_view(), name='account-profile'),
    path('users/<int:user__pk>/upload_picture/', views.MemberProfileImageUploadView.as_view(),
         name='profile-avatar-upload'),
] + router.urls
