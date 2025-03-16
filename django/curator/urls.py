from django.urls import path

from . import views

app_name = "curator"

urlpatterns = [
    path(
        "tagcleanup/process/",
        views.process_pending_tag_cleanups,
        name="process_tagcleanups",
    ),
    path(
        "admin/confirm-spam/<int:instance_id>/",
        views.confirm_spam_view,
        name="confirm_spam",
    ),
    path(
        "admin/reject-spam/<int:instance_id>/",
        views.reject_spam_view,
        name="reject_spam",
    ),
    path(
        "api/spam/get-latest-batch/",
        views.get_latest_spam_batch,
        name="get_latest_spam_batch",
    ),
    path(
        "api/spam/update/", views.update_spam_moderation, name="update_spam_moderation"
    ),
]
