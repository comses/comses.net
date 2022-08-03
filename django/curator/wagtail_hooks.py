from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from enum import Enum

from wagtail.admin.ui.components import Component
from wagtail.contrib.modeladmin.helpers import ButtonHelper, PermissionHelper
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    modeladmin_register,
    WagtailRegisterable,
)
from wagtail.contrib.modeladmin.views import IndexView
from wagtail import hooks

from core.models import Event, Job
from library.models import CodebaseRelease, PeerReview
from .models import TagCleanup


class TagCleanupPermissionHelper(PermissionHelper):
    def user_can_delete_obj(self, user, obj):
        """Don't allow deletion of inactive permission tag cleanup objs"""
        if obj.transaction_id is None:
            return super().user_can_delete_obj(user, obj)
        return False


class TagCleanupAction(Enum):
    process = "Migrate Pending Changes"
    delete_all_active = "Delete All Active Changes"
    find_by_porter_stemmer = "Porter Stemmer"
    find_by_platform_and_language = "Platform and Language"


class TagCleanupButtonHelper(ButtonHelper):
    def _action_button(self, action, label, title, classnames_add, classnames_exclude):
        if classnames_add is None:
            classnames_add = []
        if classnames_exclude is None:
            classnames_exclude = []
        classnames = ["icon-play"] + classnames_add
        cn = self.finalise_classname(classnames, classnames_exclude)
        return {
            "url": reverse("curator:process_tagcleanups"),
            "action": action,
            "label": label,
            "classname": cn,
            "title": title,
        }

    def process_button(self, classnames_add=None, classnames_exclude=None):
        return self._action_button(
            action=TagCleanupAction.process.name,
            label=TagCleanupAction.process.value,
            title=TagCleanupAction.process.value,
            classnames_add=classnames_add,
            classnames_exclude=classnames_exclude,
        )

    def delete_active_button(self, classnames_add=None, classnames_exclude=None):
        return self._action_button(
            action=TagCleanupAction.delete_all_active.name,
            label=TagCleanupAction.delete_all_active.value,
            title=TagCleanupAction.delete_all_active.value,
            classnames_add=classnames_add,
            classnames_exclude=classnames_exclude,
        )

    def find_groups_by_porter_stemmer_button(
        self, classnames_add=None, classnames_exclude=None
    ):
        return self._action_button(
            action=TagCleanupAction.find_by_porter_stemmer.name,
            label=TagCleanupAction.find_by_porter_stemmer.value,
            title=TagCleanupAction.find_by_porter_stemmer.value,
            classnames_add=classnames_add,
            classnames_exclude=classnames_exclude,
        )

    def find_groups_by_platform_and_language_button(
        self, classnames_add=None, classnames_exclude=None
    ):
        return self._action_button(
            action=TagCleanupAction.find_by_platform_and_language.name,
            label=TagCleanupAction.find_by_platform_and_language.value,
            title=TagCleanupAction.find_by_platform_and_language.value,
            classnames_add=classnames_add,
            classnames_exclude=classnames_exclude,
        )


class TagCleanupIndexView(IndexView):
    template_name = "modeladmin/curator/tagcleanup/index.html"


class TagCleanupAdmin(ModelAdmin):
    model = TagCleanup
    button_helper_class = TagCleanupButtonHelper
    permission_helper_class = TagCleanupPermissionHelper
    index_view_class = TagCleanupIndexView
    list_display = (
        "old_name",
        "new_name",
        "transaction",
    )
    list_filter = ("transaction__date_created",)
    search_fields = (
        "old_name",
        "new_name",
    )
    ordering = ("id",)


@hooks.register("construct_homepage_panels")
def add_recent_activity_panel(request, panels):
    panels.append(RecentActivityPanel())


class RecentActivityPanel(Component):
    template_name = "curator/panels/recent_activity.html"
    name = "site_recent_activity"
    order = 100

    def get_context_data(self, parent_context):
        context = super().get_context_data(parent_context)
        max_items = settings.ADMIN_DASHBOARD_MAX_ITEMS
        start_date = datetime.now(timezone.utc) - timedelta(
            days=settings.ADMIN_DASHBOARD_DAYS
        )
        new_accounts = (
            get_user_model()
            .objects.exclude(username="AnonymousUser")
            .filter(date_joined__gt=start_date)
            .order_by("-date_joined")
        )
        modified_releases = (
            CodebaseRelease.objects.filter(last_modified__gt=start_date)
            .select_related("submitter")
            .order_by("-last_modified")
        )
        modified_events = (
            Event.objects.filter(last_modified__gt=start_date)
            .select_related("submitter")
            .order_by("-last_modified")
        )
        modified_jobs = (
            Job.objects.filter(last_modified__gt=start_date)
            .select_related("submitter")
            .order_by("-last_modified")
        )
        modified_peer_reviews = (
            PeerReview.objects.filter(last_modified__gt=start_date)
            .select_related("codebase_release", "submitter")
            .order_by("-last_modified")
        )

        context.update(
            {
                "start_date": start_date,
                "new_accounts_count": new_accounts.count(),
                "new_accounts": new_accounts[:max_items],
                "max_size": max_items,
                "modified_events_count": modified_events.count(),
                "modified_events": modified_events[:max_items],
                "modified_jobs_count": modified_jobs.count(),
                "modified_jobs": modified_jobs[:max_items],
                "modified_releases_count": modified_releases.count(),
                "modified_releases": modified_releases[:max_items],
                "modified_reviews_count": modified_peer_reviews.count(),
                "modified_reviews": modified_peer_reviews[:max_items],
            }
        )
        return context


modeladmin_register(TagCleanupAdmin)
