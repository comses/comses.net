from django.contrib.auth.decorators import permission_required
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_POST

from wagtail.contrib.modeladmin.helpers import AdminURLHelper

from curator.models import PendingTagCleanup
from curator.wagtail_hooks import PendingTagCleanupButtonHelper


class Http400(Exception): pass


@require_POST
@permission_required('curator.process_pendingtagcleanup', raise_exception=True)
def process_pending_tag_cleanups(request):
    action = request.POST['action']
    if action == PendingTagCleanup.objects.process.__name__:
        PendingTagCleanup.objects.process()
    elif action == PendingTagCleanup.find_groups_by_porter_stemmer.__name__:
        PendingTagCleanup.objects.bulk_create(PendingTagCleanup.find_groups_by_porter_stemmer())
    elif action == PendingTagCleanup.find_groups_by_platform_and_language.__name__:
        PendingTagCleanup.objects.bulk_create(PendingTagCleanup.find_groups_by_platform_and_language())
    elif action == PendingTagCleanupButtonHelper.DELETE_ALL_ACTIVE:
        PendingTagCleanup.objects.filter(is_active=True).delete()
    else:
        return Http400('{} not a valid action'.format(action))
    return HttpResponseRedirect(
        AdminURLHelper(PendingTagCleanup).index_url
    )