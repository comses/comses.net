from wagtail.contrib.modeladmin.options import (ModelAdmin, modeladmin_register, ModelAdminGroup)

from django.utils.translation import ugettext_lazy as _
from .models import CodebaseImage, PeerReview, PeerReviewerFeedback, PeerReviewInvitation


class CodebaseImageAdmin(ModelAdmin):
    model = CodebaseImage
    list_display = ('title', 'file',)
    search_fields = ('title',)


modeladmin_register(CodebaseImageAdmin)


class PeerReviewAdmin(ModelAdmin):
    model = PeerReview
    list_display = ('status', 'codebase_release__title', 'reviewer_recommendation', 'date_created')
    list_filter = ('status', 'date_created',)
    search_fields = ('submitter', 'codebase_release__title')


class PeerReviewerFeedbackAdmin(ModelAdmin):
    model = PeerReviewerFeedback
    list_display = ('date_created', 'recommendation', 'reviewer')
    list_filter = ('date_created', 'recommendation', 'reviewer')


class PeerReviewInvitationAdmin(ModelAdmin):
    model = PeerReviewInvitation
    list_display = ('date_created', 'review__codebase_release', 'candidate_reviewer', )
    list_filter = ('date_created', 'review__codebase_release', 'candidate_reviewer', )


class PeerReviewGroup(ModelAdminGroup):
    menu_label = 'Peer Review'
    menu_icon = 'folder-open-inverse'
    label = _('Peer Review')
    items = (PeerReviewAdmin, PeerReviewerFeedbackAdmin, PeerReviewInvitationAdmin, )


modeladmin_register(PeerReviewGroup)