import logging

from django.core.management.base import BaseCommand

from curator.tag_deduplication import TagGazetteer
from curator.models import CanonicalTag

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Searches for canonical tags that most closely match a tag name"

    def add_arguments(self, parser):
        parser.add_argument("--search", default="")
        parser.add_argument(
            "--label",
            "-l",
            help="Label the training data for the gazetteering model using the console",
            action="store_true",
            default=False,
        )
        parser.add_argument(
            "--threshold",
            "-t",
            help="Threshold to use for clustering tags",
            action="store_true",
            default=0.5,
        )

    def handle(self, *args, **options):
        if not CanonicalTag.objects.exists():
            logger.warn(
                "Canonical list is empty, populating canonical list using the curator_cluster_tags command"
            )
            return

        tag_gazetteering = TagGazetteer(options["threshold"])

        if options["label"]:
            tag_gazetteering.console_label()
            tag_gazetteering.save_to_training_file()

        if options["search"] != "":
            if not tag_gazetteering.training_file_exists():
                logging.warn(
                    "Your model does not have any labelled data. Run this command with --label and try again."
                )

            search_results = tag_gazetteering.human_readable_search(options["search"])
            logger.debug("Searching for tags that closely match: %s", options["search"])

            if len(search_results) == 0:
                logger.debug("no matching tags found")

            else:
                logger.debug(
                    "The following tags seem to closely match the tag: %s",
                    search_results,
                )
