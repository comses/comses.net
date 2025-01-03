import logging

from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Codebase, CodebaseRelease
from .tasks import update_mirrored_release_metadata, update_mirrored_codebase_metadata
from .metadata import CodebaseReleaseMetadataBuilder

logger = logging.getLogger(__name__)


@receiver(
    post_save, sender=CodebaseRelease, dispatch_uid="update_mirrored_release_metadata"
)
def on_codebase_release_save(sender, instance: CodebaseRelease, **kwargs):
    """
    * update the cached codemeta JSON for the release
    * update the metadata in the git mirror for a codebase release if it has a git mirror
      and the metadata changed
    """
    logger.debug("RELEASE SAVED")
    release = instance
    CodebaseReleaseMetadataBuilder(release).build_codemeta_and_cache()

    codebase = release.codebase
    mirror = codebase.git_mirror
    if mirror and mirror.remote_url:
        update_mirrored_release_metadata(release.id)


@receiver(post_save, sender=Codebase, dispatch_uid="update_mirrored_codebase_metadata")
def on_codebase_save(sender, instance: Codebase, **kwargs):
    """
    * update the cached codemeta JSON for all releases of the codebase
    * update the metadata in the git mirror for a codebase if it has a git mirror
      and the metadata changed
    """
    codebase = instance
    for release in codebase.releases.all():
        CodebaseReleaseMetadataBuilder(release).build_codemeta_and_cache()
    mirror = codebase.git_mirror
    if mirror and mirror.remote_url:
        update_mirrored_codebase_metadata(codebase.id)
