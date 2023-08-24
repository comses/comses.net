import logging

from django.core.management.base import BaseCommand

from curator.tag_deduplication import TagClusterer


class Command(BaseCommand):
    help = """
    Cluster Tags using dedupe. This command takes the rows of tags available in the database and clusters the tags together using Dedupe. 
    It takes in the rows available in the Tag table and attempts to create CanonicalTag objects that are stored in the database.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--run",
            "-r",
            help="run the clustering model.",
            action="store_true",
            default=False,
        )

        parser.add_argument(
            "--label",
            "-l",
            help="label the training data for the gazetteering model using the console.",
            action="store_true",
            default=False,
        )

        parser.add_argument(
            "--save",
            "-s",
            help="save the clustering results to the database in CanonicalTag.",
            action="store_true",
            default=False,
        )

        parser.add_argument(
            "--threshold",
            "-t",
            help="""float between [0,1]. Blank defaults to 0.5. 
            Defines how much confidence to require from the model before tags are clustered. 
            Higher thresholds cluster less tags and require more training data labels.""",
            action="store_true",
            default=0.5,
        )

    def handle(self, *args, **options):
        """
        `curator_cluster_tags should be used only if the curator would like for a large amount of unlabelled tags to be clustered.
        For individual tags, the TagGazetteer is more preferred.
        """
        tag_clusterer = TagClusterer(clustering_threshold=options["threshold"])

        if options["label"]:
            tag_clusterer.console_label()
            tag_clusterer.save_to_training_file()

        if options["run"]:
            if not tag_clusterer.training_file_exists():
                logging.warn(
                    "Your model does not have any labelled data. Run this command with --label and try again."
                )

            clusters = tag_clusterer.cluster_tags()
            if options["save"]:
                tag_clusterer.save_clusters(clusters)
