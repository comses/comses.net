from django.contrib.auth.decorators import permission_required
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from wagtail.contrib.modeladmin.helpers import AdminURLHelper

from curator.models import TagCleanup
from curator.wagtail_hooks import TagCleanupAction

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
