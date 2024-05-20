from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.urls import reverse
from django.views.decorators.http import require_POST
from wagtail_modeladmin.helpers import AdminURLHelper

from curator.models import TagCleanup
from curator.wagtail_hooks import TagCleanupAction
from core.models import SpamModeration

import bleach

TAG_CLEANUP_ACTIONS = {
    TagCleanupAction.process.name: TagCleanup.objects.process,
    TagCleanupAction.find_by_porter_stemmer.name: lambda: TagCleanup.objects.bulk_create(
        TagCleanup.find_groups_by_porter_stemmer()
    ),
    TagCleanupAction.find_by_platform_and_language.name: lambda: TagCleanup.objects.bulk_create(
        TagCleanup.find_groups_by_platform_and_language()
    ),
    TagCleanupAction.delete_all_active.name: lambda: TagCleanup.objects.filter(
        transaction_id__isnull=True
    ).delete(),
}


@require_POST
@permission_required("curator.process_tagcleanup", raise_exception=True)
def process_pending_tag_cleanups(request):
    action_name = request.POST["action"]
    action = TAG_CLEANUP_ACTIONS.get(action_name)
    if not action:
        return HttpResponseBadRequest(f"invalid action: {bleach.clean(action_name)}")
    action()
    return HttpResponseRedirect(AdminURLHelper(TagCleanup).index_url)


def confirm_spam_view(request, instance_id):
    spam_moderation = get_object_or_404(SpamModeration, id=instance_id)
    deactivate_user = request.GET.get("deactivate_user") == "true"
    if deactivate_user:
        user = spam_moderation.content_object.submitter
        user.is_active = False
        user.save()
        messages.success(
            request, f"Content confirmed as spam and user: {user} deactivated."
        )
    spam_moderation.status = SpamModeration.Status.SPAM
    spam_moderation.reviewer = request.user
    spam_moderation.save()
    messages.success(request, f"Content confirmed as spam.")
    return HttpResponseRedirect(AdminURLHelper(SpamModeration).index_url)


def reject_spam_view(request, instance_id):
    spam_moderation = get_object_or_404(SpamModeration, id=instance_id)
    spam_moderation.status = SpamModeration.Status.NOT_SPAM
    spam_moderation.reviewer = request.user
    spam_moderation.save()
    messages.success(request, "Content marked as not spam.")
    return HttpResponseRedirect(AdminURLHelper(SpamModeration).index_url)
