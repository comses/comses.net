from django.core.management.base import BaseCommand, CommandError
from library.fs import CategoryManifestManager
from library.models import CodebaseRelease


class Command(BaseCommand):
    help = (
        "Backfill missing file categories without modifying release files or metadata."
    )

    def handle(self, **options):
        count = 0
        releases = CodebaseRelease.objects.filter(category_manifest__isnull=True)
        for release in releases.iterator():
            try:
                CategoryManifestManager(release).backfill()
            except FileNotFoundError as error:
                raise CommandError(str(error)) from error
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Backfilled {count} release manifests."))
