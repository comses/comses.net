import csv
import logging
import sys
from django.core.management.base import BaseCommand
from library.doi import VERIFICATION_MESSAGE, get_welcome_message
from library.models import Codebase

logger = logging.getLogger(__name__)


def remove_existing_codebase_dois(interactive=True, dry_run=True):
    print(get_welcome_message(dry_run))
    codebases_with_dois = Codebase.objects.exclude(doi__isnull=True)

    logger.info(
        f"Removing DOIs for {len(codebases_with_dois)} Codebases. Query: Codebase.objects.exclude(doi__isnull=True) ..."
    )
    if interactive and codebases_with_dois.exists():
        confirm = input(
            "WARNING: this will remove all existing codebase DOIs and is unrecoverable. Type 'DELETE' to continue or Ctrl+C to quit: "
        )
        if confirm.lower() == "delete":
            with open("codebases_with_dois.csv", "w") as f:
                writer = csv.writer(f)
                writer.writerow(["Codebase ID", "Codebase DOI"])
                for codebase in codebases_with_dois:
                    writer.writerow([codebase.pk, codebase.doi])
            codebases_with_dois.update(doi=None)
        else:
            logger.info("Aborting.")
            sys.exit()

    logger.info(
        "All DOIs from {len(codebases_with_dois)} codebases deleted successfully."
    )

    """
    assert correctness
    """
    if not dry_run:
        print(VERIFICATION_MESSAGE)
        assert Codebase.objects.filter(doi__isnull=False).count() == 0
        logger.info("Success. All existing codebase DOIs deleted.")


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            "--interactive",
            action="store_true",
            help="Wait for user to press enter to continue.",
            default=True,
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Output what would have happened."
        )

    def handle(self, *args, **options):
        interactive = options["interactive"]
        dry_run = options["dry_run"]
        remove_existing_codebase_dois(interactive, dry_run)
