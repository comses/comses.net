from enum import Enum

from django.urls import reverse
from wagtail.contrib.modeladmin.helpers import ButtonHelper, PermissionHelper
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register
from wagtail.contrib.modeladmin.views import IndexView

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


modeladmin_register(TagCleanupAdmin)
