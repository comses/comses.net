import logging

from django.core.management.base import BaseCommand
from curator.spam import SpamDetector

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Perform spam detection"

    def __init__(self):
        self.detection = SpamDetector()
        self.processor = self.detection.processor
        self.user_meta_classifier = self.detection.user_metadata_classifier
        self.text_classifier = self.detection.text_classifier

    def add_arguments(self, parser):
        parser.add_argument(
            "--exe",
            "-e",
            action="store_true",
            default=False,
            help="Print user_ids of spam users and the metrics of the models used to obtain the predictions.",
        )
        parser.add_argument(
            "--get_model_metrics",
            "-m",
            action="store_true",
            default=False,
            help="Print the accuracy, precision, recall and f1 scores of the models used to obtain the predictions.",
        )
        parser.add_argument(
            "--load_labels",
            "-l",
            action="store_true",
            default=False,
            help="Store manually annotated spam labels to the DB.",
        )
        parser.add_argument(
            "--fit_usermeta_model", "-fu", action="store_true", default=False
        )
        parser.add_argument(
            "--fit_text_model", "-ft", action="store_true", default=False
        )
        parser.add_argument(
            "--predict_usermeta_model",
            "-pu",
            action="store_true",
            default=False,
            help="Print user_ids of all the evaluated users and spam users using the UserMetadata model",
        )
        parser.add_argument(
            "--predict_text_model",
            "-pt",
            action="store_true",
            default=False,
            help="Print user_ids of all the evaluated users and spam users using the Text model",
        )

    def handle_exe(self):
        self.detection.execute()

    def handle_get_model_metrics(self):
        self.detection.get_model_metrics()

    def handle_load_labels(self):
        self.processor.load_labels_from_csv()

    def handle_fit_usermeta_model(self):
        self.detection.fit_usermeta_spam_classifier()

    def handle_fit_text_model(self):
        self.detection.fit_text_spam_classifier()

    def handle_predict_usermeta_model(self):
        self.detection.predict_usermeta_spam_classifier()

    def handle_predict_text_model(self):
        self.detection.predict_text_spam_classifier()

    def handle(self, *args, **options):
        if options["exe"]:
            action = "exe"
        elif options["get_model_metrics"]:
            action = "get_model_metrics"
        elif options["load_labels"]:
            action = "load_labels"
        elif options["fit_usermeta_model"]:
            action = "fit_usermeta_model"
        elif options["fit_text_model"]:
            action = "fit_text_model"
        elif options["predict_usermeta_model"]:
            action = "predict_usermeta_model"
        elif options["predict_text_model"]:
            action = "predict_text_model"

        getattr(self, f"handle_{action}")()
