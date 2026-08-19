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
        "admin/mark-user-spam/<int:user_id>/",
        views.mark_user_as_spam,
        name="mark_user_spam",
    ),
]
