import logging

from django.core.management.base import BaseCommand

from curator.tag_deduplication import TagGazetteer
from curator.models import CanonicalTag

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Matches tags to a canonical list of tags using dedupe. This command finds a canonical tag "

    def add_arguments(self, parser):
        parser.add_argument(
            "--search",
            default="",
            help="str to search for. Dedupe will search for a canonical tag that most closely matches this.",
        )
        parser.add_argument(
            "--label",
            "-l",
            help="label the training data for the gazetteering model using the console",
            action="store_true",
            default=False,
        )
        parser.add_argument(
            "--threshold",
            "-t",
            help="""float between [0,1]. Blank defaults to 0.5. 
            Defines how much confidence to require from the model before tags are selected from the canonical list. 
            Higher thresholds matches less tags to those in a canonical list and require more training data labels.""",
            action="store_true",
            default=0.5,
        )

    def handle(self, *args, **options):
        if len(CanonicalTag.objects.all()) == 0:
            logger.warn(
                "Canonical list is empty, populating canonical list using the curator_cluster_tags command"
            )
            return

        tag_gazetteer = TagGazetteer(options["threshold"])

        if options["label"]:
            tag_gazetteer.console_label()
            tag_gazetteer.save_to_training_file()

        if options["search"] != "":
            if not tag_gazetteer.training_file_exists():
                logging.warn(
                    "Your model does not have any labelled data. Run this command with --label and try again."
                )

            search_results = tag_gazetteer.human_readable_search(options["search"])
            print("Searching for tags that closely match: ", options["search"])

            if len(search_results) == 0:
                print(
                    "There are no tags that closely match the name you were searching for"
                )

            else:
                print("The following tags seem to closely match the tag")
                print(search_results)
