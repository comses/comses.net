from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.conf.urls import url
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Permission, User
from django.forms import Media
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.generic import TemplateView
from enum import Enum

from wagtail.admin.menu import MenuItem
from wagtail.admin.navigation import get_site_for_user
from wagtail.admin.site_summary import SiteSummaryPanel
from wagtail.admin.views.home import UpgradeNotificationPanel, PagesForModerationPanel, RecentEditsPanel
from wagtail.contrib.modeladmin.helpers import ButtonHelper, PermissionHelper
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register, WagtailRegisterable
from wagtail.contrib.modeladmin.views import IndexView
from wagtail.core.hooks import get_hooks

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
    process = 'Migrate Pending Changes'
    delete_all_active = 'Delete All Active Changes'
    find_by_porter_stemmer = 'Porter Stemmer'
    find_by_platform_and_language = 'Platform and Language'


class TagCleanupButtonHelper(ButtonHelper):
    def _action_button(self, action, label, title, classnames_add, classnames_exclude):
        if classnames_add is None:
            classnames_add = []
        if classnames_exclude is None:
            classnames_exclude = []
        classnames = ['icon-play'] + classnames_add
        cn = self.finalise_classname(classnames, classnames_exclude)
        return {
            'url': reverse('curator:process_tagcleanups'),
            'action': action,
            'label': label,
            'classname': cn,
            'title': title,
        }

    def process_button(self, classnames_add=None, classnames_exclude=None):
        return self._action_button(action=TagCleanupAction.process.name,
                                   label=TagCleanupAction.process.value,
                                   title=TagCleanupAction.process.value,
                                   classnames_add=classnames_add,
                                   classnames_exclude=classnames_exclude)

    def delete_active_button(self, classnames_add=None, classnames_exclude=None):
        return self._action_button(action=TagCleanupAction.delete_all_active.name,
                                   label=TagCleanupAction.delete_all_active.value,
                                   title=TagCleanupAction.delete_all_active.value,
                                   classnames_add=classnames_add,
                                   classnames_exclude=classnames_exclude)

    def find_groups_by_porter_stemmer_button(self, classnames_add=None, classnames_exclude=None):
        return self._action_button(action=TagCleanupAction.find_by_porter_stemmer.name,
                                   label=TagCleanupAction.find_by_porter_stemmer.value,
                                   title=TagCleanupAction.find_by_porter_stemmer.value,
                                   classnames_add=classnames_add,
                                   classnames_exclude=classnames_exclude)

    def find_groups_by_platform_and_language_button(self, classnames_add=None, classnames_exclude=None):
        return self._action_button(action=TagCleanupAction.find_by_platform_and_language.name,
                                   label=TagCleanupAction.find_by_platform_and_language.value,
                                   title=TagCleanupAction.find_by_platform_and_language.value,
                                   classnames_add=classnames_add,
                                   classnames_exclude=classnames_exclude)


class TagCleanupIndexView(IndexView):
    template_name = 'modeladmin/curator/tagcleanup/index.html'


class TagCleanupAdmin(ModelAdmin):
    model = TagCleanup
    button_helper_class = TagCleanupButtonHelper
    permission_helper_class = TagCleanupPermissionHelper
    index_view_class = TagCleanupIndexView
    list_display = ('old_name', 'new_name', 'transaction',)
    list_filter = ('transaction__date_created',)
    search_fields = ('old_name', 'new_name',)
    ordering = ('id',)


class RecentActivityPanel:
    name = 'site_recent_activity'
    order = 100

    def __init__(self, request):
        self.request = request

    def render(self):
        start_date = datetime.now(timezone.utc) - timedelta(days=90)
        max_size = 10
        new_accounts = User.objects.exclude(username='AnonymousUser').filter(date_joined__gt=start_date).order_by(
            '-date_joined')
        modified_releases = CodebaseRelease.objects.filter(last_modified__gt=start_date).select_related(
            'submitter').order_by('-last_modified')
        modified_events = Event.objects.filter(last_modified__gt=start_date).select_related('submitter').order_by(
            '-last_modified')
        modified_jobs = Job.objects.filter(last_modified__gt=start_date).select_related('submitter').order_by(
            '-last_modified')
        modified_peer_reviews = PeerReview.objects.filter(last_modified__gt=start_date) \
            .select_related('codebase_release', 'submitter').order_by('-last_modified')

        return render_to_string('curator/home/recent_activity.html', {
            'start_date': start_date,
            'new_accounts_count': new_accounts.count(),
            'new_accounts': new_accounts[:max_size],
            'max_size': max_size,
            'modified_events_count': modified_events.count(),
            'modified_events': modified_events[:max_size],
            'modified_jobs_count': modified_jobs.count(),
            'modified_jobs': modified_jobs[:max_size],
            'modified_releases_count': modified_releases.count(),
            'modified_releases': modified_releases[:max_size],
            'modified_reviews_count': modified_peer_reviews.count(),
            'modified_reviews': modified_peer_reviews[:max_size]
        }, request=self.request)


class DashboardView(PermissionRequiredMixin, TemplateView):
    template_name = 'curator/dashboard.html'
    permission_required = 'wagtailadmin.access_admin'

    def get_login_url(self):
        return '{}?next={}'.format(reverse('wagtailadmin_login'), reverse('wagtailadmin_home'))

    def get_context_data(self, **kwargs):
        request = self.request
        panels = [
            SiteSummaryPanel(request),
            UpgradeNotificationPanel(),
            PagesForModerationPanel(),
            RecentEditsPanel(),
            RecentActivityPanel(request)
        ]

        for fn in get_hooks('construct_homepage_panels'):
            fn(request, panels)

        media = Media()
        for panel in panels:
            if hasattr(panel, 'media'):
                media += panel.media

        site_details = get_site_for_user(request.user)

        return {
            'root_page': site_details['root_page'],
            'root_site': site_details['root_site'],
            'site_name': site_details['site_name'],
            'panels': sorted(panels, key=lambda p: p.order),
            'user': request.user,
            'media': media,
        }


class Dashboard(WagtailRegisterable):
    add_to_settings_menu = False

    def get_permissions_for_registration(self):
        return Permission.objects.none()

    def get_admin_urls_for_registration(self):
        return [url(r'^%s/%s/$' % ('curator', 'dashboard'), view=self.dashboard_view, name='wagtailadmin_dashboard')]

    def get_menu_item(self):
        return MenuItem(label='Dashboard', url=reverse('wagtailadmin_dashboard'), order=999)

    def dashboard_view(self, request):
        return DashboardView.as_view()(request)


modeladmin_register(TagCleanupAdmin)
