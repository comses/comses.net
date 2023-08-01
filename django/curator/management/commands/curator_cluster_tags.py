import logging

from django.core.management.base import BaseCommand

from curator.tag_deduplication import TagClustering


class Command(BaseCommand):
    help = "Cluster Tags using dedupe"

    def add_arguments(self, parser):
        parser.add_argument(
            "--run",
            "-r",
            help="Run the clustering model",
            action="store_true",
            default=False,
        )

        parser.add_argument(
            "--label",
            "-l",
            help="Label the data via the console",
            action="store_true",
            default=False,
        )

        parser.add_argument(
            "--save",
            "-s",
            help="Save the clustering results to the database",
            action="store_true",
            default=False,
        )

    def handle(self, *args, **options):
        tag_gazetteering = TagClustering()

        if options["label"]:
            tag_gazetteering.console_label()
            tag_gazetteering.save_to_training_file()

        if options["run"]:
            if not tag_gazetteering.training_file_exists():
                logging.warn(
                    "Your model does not have any labelled data. Run this command with --label and try again."
                )

            clusters = tag_gazetteering.cluster_tags()
            if options["save"]:
                tag_gazetteering.save_clusters(clusters)
