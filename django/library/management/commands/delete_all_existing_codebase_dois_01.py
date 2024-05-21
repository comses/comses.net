import logging
from django.core.management.base import BaseCommand
from library.models import Codebase
from library.doi import VERIFICATION_MESSAGE, get_welcome_message

logger = logging.getLogger(__name__)

def delete_all_existing_codebase_dois_01(interactive=True, dry_run=True):
    print(get_welcome_message(dry_run))
    codebases_with_dois = Codebase.objects.exclude(doi__isnull=True)

    logger.info(
        f"Deleting DOIs for {len(codebases_with_dois)} Codebases. Query: Codebase.objects.exclude(doi__isnull=True) ..."
    )

    for i, codebase in enumerate(codebases_with_dois):
        logger.debug(
            f"Deleting DOI {i+1}/{len(codebases_with_dois)}: {codebase.doi} from codebase {codebase.pk} ..."
        )
        if interactive:
            input("Press Enter to continue or CTRL+C to quit...")

        if not dry_run:
            codebase.doi = None
            codebase.save()

    logger.info(
        f"All DOIs from {len(codebases_with_dois)} codebases deleted successfully."
    )

    """
    assert correctness
    """
    if not dry_run:
        print(VERIFICATION_MESSAGE)
        logger.info("Checking that all existing codebase DOIs have been deleted...")
        for i, codebase in enumerate(codebases_with_dois):
            print(f"Processing Codebase {i}/{len(codebases_with_dois)} {'' if (i+1)%8 == 0 else '.'*((i+1)%8)}", end=" \r")
            if codebase.doi is not None:
                logger.error(f"DOI for codebase {codebase.pk} should be None!")
        logger.info("Success. All existing codebase DOIs deleted.")

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--interactive', action='store_true', help='Wait for user to press enter to continue.')
        parser.add_argument('--dry-run', action='store_true', help='Output what would have happened.')

    def handle(self, *args, **options):
        interactive = options['interactive']
        dry_run = options['dry_run']
        delete_all_existing_codebase_dois_01(interactive, dry_run)