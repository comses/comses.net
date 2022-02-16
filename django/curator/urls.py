from django.urls import path

from . import views

app_name = "curator"

urlpatterns = [
    path(
        "tagcleanup/process/",
        views.process_pending_tag_cleanups,
        name="process_tagcleanups",
    ),
]
