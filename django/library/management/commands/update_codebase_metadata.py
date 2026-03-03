import json
import logging

from django.core.management.base import BaseCommand

from library.models import Codebase, CodebaseRelease

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Update stored codemeta representation of metadata for all codebases and releases.
    Rebuilds the archive package on the filesystem

    This is intended to be run as a one-off command to update codemeta for all records
    after a change to how codemeta is stored, generated, and used.
    """

    def handle(self, *args, **options):
        self.stdout.write("Updating codemeta for all Codebase objects...")
        self.update_codemeta(Codebase)
        self.stdout.write("Updating codemeta for all CodebaseRelease objects...")
        self.update_codemeta(CodebaseRelease)
        self.stdout.write("Rebuilding fs packages for all releases...")
        self.update_release_packages()
        self.stdout.write("Done")

    def update_codemeta(self, model):
        objects = model.objects.all()
        total = objects.count()
        errors = []
        for obj in objects:
            try:
                fresh_codemeta = obj.codemeta.dict(serialize=True)
                model.objects.filter(pk=obj.pk).update(codemeta_snapshot=fresh_codemeta)
            except Exception as e:
                errors.append((obj, e))
        if errors:
            for obj, e in errors:
                logger.error(f"Error updating codemeta for {obj}: {e}")
            self.stdout.write(
                f"Updated codemeta for {total - len(errors)}/{total} {model.__name__} objects"
            )
            self.stdout.write(f"with {len(errors)} errors")
        else:
            self.stdout.write(f"Updated codemeta for {total} {model.__name__} objects")

    def update_release_packages(self):
        releases = CodebaseRelease.objects.all()
        total = releases.count()
        errors = []
        for release in releases:
            try:
                fs_api = release.get_fs_api()
                fs_api.rebuild(metadata_only=True)
            except Exception as e:
                errors.append((release, e))
        if errors:
            for release, e in errors:
                logger.error(f"Error updating metadata for {release}: {e}")
            self.stdout.write(
                f"Updated metadata for {total - len(errors)}/{total} release packages"
            )
            self.stdout.write(f"with {len(errors)} errors")
        else:
            self.stdout.write(f"Updated metadata for {total} release packages")
