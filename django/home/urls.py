from django.urls import path, re_path
from wagtail.images.views.serve import ServeView

from . import views

app_name = "home"

urlpatterns = [
    path("about/metrics/", views.MetricsView.as_view(), name="metrics"),
    path("search/", views.SearchView.as_view(), name="search"),
    path("digest/", views.DigestView.as_view(), name="digest"),
    path(
        "conference/<int:slug>/submit/",
        views.ConferenceSubmissionView.as_view(),
        name="submit-conference",
    ),
    re_path(
        r"^images/([^/]*)/(\d*)/([^/]*)/[^/]*$",
        ServeView.as_view(),
        name="wagtailimages_serve",
    ),
    path("about/contact/sent/", views.ContactSentView.as_view(), name="contact-sent"),
]
