from django.urls import reverse
from wagtail.contrib.modeladmin.helpers import ButtonHelper, PermissionHelper
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register
from wagtail.contrib.modeladmin.views import IndexView

from .models import PendingTagCleanup


class PendingTagCleanupPermissionHelper(PermissionHelper):
    def user_can_delete_obj(self, user, obj):
        """Don't allow deletion of inactive permission tag cleanup objs"""
        if obj.is_active:
            return super().user_can_delete_obj(user, obj)
        return False


class PendingTagCleanupButtonHelper(ButtonHelper):
    def _action_button(self, action, label, title, classnames_add, classnames_exclude):
        if classnames_add is None:
            classnames_add = []
        if classnames_exclude is None:
            classnames_exclude = []
        classnames = ['icon-play'] + classnames_add
        cn = self.finalise_classname(classnames, classnames_exclude)
        return {
            'url': reverse('curator:process_pendingtagcleanups'),
            'action': action,
            'label': label,
            'classname': cn,
            'title': title,
        }

    DELETE_ALL_ACTIVE = 'delete_all_active'

    def process_button(self, classnames_add=None, classnames_exclude=None):
        return self._action_button(action=PendingTagCleanup.objects.process.__name__,
                                   label='Migrate Pending Changes',
                                   title='Migrate Pending Changes',
                                   classnames_add=classnames_add,
                                   classnames_exclude=classnames_exclude)

    def delete_active_button(self, classnames_add=None, classnames_exclude=None):
        return self._action_button(action=self.DELETE_ALL_ACTIVE,
                                   label='Delete All Active Changes',
                                   title='Delete All Active Changes',
                                   classnames_add=classnames_add,
                                   classnames_exclude=classnames_exclude)

    def find_groups_by_porter_stemmer_button(self, classnames_add=None, classnames_exclude=None):
        return self._action_button(action=PendingTagCleanup.find_groups_by_porter_stemmer.__name__,
                                   label='Porter Stemmer',
                                   title='Porter Stemmer',
                                   classnames_add=classnames_add,
                                   classnames_exclude=classnames_exclude)

    def find_groups_by_platform_and_language_button(self, classnames_add=None, classnames_exclude=None):
        return self._action_button(action=PendingTagCleanup.find_groups_by_porter_stemmer.__name__,
                                   label='Platform and Language',
                                   title='Platform and Language',
                                   classnames_add=classnames_add,
                                   classnames_exclude=classnames_exclude)


class PendingTagCleanupIndexView(IndexView):
    template_name = 'modeladmin/curator/pendingtagcleanup/index.html'


class PendingTagCleanupAdmin(ModelAdmin):
    model = PendingTagCleanup
    button_helper_class = PendingTagCleanupButtonHelper
    permission_helper_class = PendingTagCleanupPermissionHelper
    index_view_class = PendingTagCleanupIndexView
    list_display = ('old_name', 'new_name', 'transaction_id',)
    list_filter = ('is_active',)
    search_fields = ('old_name', 'new_name',)
    ordering = ('id',)


modeladmin_register(PendingTagCleanupAdmin)
