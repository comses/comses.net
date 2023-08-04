from django.urls import path, re_path
from rest_framework.routers import SimpleRouter
from wagtail.images.views.serve import ServeView

from . import views

app_name = "home"

router = SimpleRouter()
router.register(r"tags", views.TagListView, basename="tag")
router.register(r"events", views.EventViewSet, basename="event")
router.register(r"jobs", views.JobViewSet, basename="job")
router.register(r"users", views.ProfileViewSet, basename="profile")

urlpatterns = [
    path("about/metrics/", views.MetricsView.as_view(), name="metrics"),
    path("search/", views.SearchView.as_view(), name="search"),
    path("digest/", views.DigestView.as_view(), name="digest"),
    path(
        "conference/<int:slug>/submit/",
        views.ConferenceSubmissionView.as_view(),
        name="submit-conference",
    ),
    path("users/follow/", views.ToggleFollowUser.as_view(), name="follow-user"),
    re_path(
        r"^images/([^/]*)/(\d*)/([^/]*)/[^/]*$",
        ServeView.as_view(),
        name="wagtailimages_serve",
    ),
    path(
        "events/<int:pk>/delete/",
        views.EventMarkDeletedView.as_view(),
        name="event-delete",
    ),
    path("events/<int:pk>/edit/", views.EventUpdateView.as_view(), name="event-edit"),
    path("events/add/", views.EventCreateView.as_view(), name="event-add"),
    path(
        "jobs/<int:pk>/delete/", views.JobMarkDeletedView.as_view(), name="job-delete"
    ),
    path("jobs/<int:pk>/edit/", views.JobUpdateView.as_view(), name="job-edit"),
    path("jobs/add/", views.JobCreateView.as_view(), name="job-add"),
    path("about/contact/sent/", views.ContactSentView.as_view(), name="contact-sent"),
    path(
        "users/<int:user__pk>/edit/",
        views.ProfileUpdateView.as_view(),
        name="profile-edit",
    ),
    path(
        "accounts/profile/", views.ProfileRedirectView.as_view(), name="account-profile"
    ),
    path(
        "users/<int:user__pk>/upload_picture/",
        views.MemberProfileImageUploadView.as_view(),
        name="profile-avatar-upload",
    ),
] + router.urls
