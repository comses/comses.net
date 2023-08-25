import logging

from django.core.management.base import BaseCommand
from taggit.models import Tag

from curator.tag_deduplication import TagGazetteer
from curator.models import CanonicalTag, CanonicalTagMapping

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Matches tags to a canonical list of tags using dedupe. This command finds a canonical tag "

    def add_arguments(self, parser):
        parser.add_argument(
            "--run",
            action="store_true",
            help="run the gazetteering model.",
            default=False,
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
        """
        `curator_gazetteer_tags` searches for CanonicalTags that most closely match a certain tag.
        From a canonical list, the canonical tag that most closely matches is selected.
        """
        if not CanonicalTag.objects.exists():
            logger.warn(
                "Canonical list is empty, populating canonical list using the curator_cluster_tags command"
            )
            return

        tag_gazetteer = TagGazetteer(options["threshold"])

        if options["label"]:
            tag_gazetteer.console_label()
            tag_gazetteer.save_to_training_file()

        if options["run"] != "":
            if not tag_gazetteer.training_file_exists():
                logging.warn(
                    "Your model does not have any labelled data. Run this command with --label and try again."
                )

            tags = Tag.objects.filter(canonicaltagmapping=None)
            is_unmatched = False
            for tag in tags:
                matches = tag_gazetteer.text_search(tag.name)
                if matches:
                    match = matches[0]
                    CanonicalTagMapping(
                        tag=tag, canonical_tag=match[0], confidence_score=match[1]
                    ).save()
                else:
                    is_unmatched = True

            if is_unmatched:
                logging.warn(
                    "There are some Tags that could not be matched to CanonicalTags. Either lower the threshold or increase the training data size."
                )
