import logging
import pathlib

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
            help="returns spam user_ids and model metrics",
        )
        parser.add_argument(
            "--get_model_metrics",
            "-g",
            action="store_true",
            default=False,
            help="gets model accuracy, precision, recall and f1 scores",
        )
        parser.add_argument(
            "--load_labels",
            "-l",
            action="store_true",
            default=False,
            help="save initial dataset to the DB. ",
        )
        parser.add_argument("--train_user", "-tu", action="store_true", default=False)
        parser.add_argument("--predict_user", "-pu", action="store_true", default=False)
        parser.add_argument("--train_text", "-tt", action="store_true", default=False)
        parser.add_argument("--predict_text", "-pt", action="store_true", default=False)

    def handle_exe(self):
        result = self.detection.execute()
        print("Spam Users :\n", result["spam_users"])
        print(
            "UserMetadataSpamClassifier Metircs :\n",
            result["user_metadata_spam_classifier"],
        )
        print("TextSpamClassifier Metircs:\n", result["text_spam_classifier"])

    def handle_get_model_metrics(self):
        metrics = self.detection.get_model_metrics()
        print(
            "UserMetadataSpamClassifier Metircs:\n",
            metrics["user_metadata_spam_classifier"],
        )
        print("TextSpamClassifier Metircs:\n", metrics["text_spam_classifier"])

    def handle_load_labels(self):
        self.processor.load_labels_from_csv()

    def handle_train_user(self):
        model_metrics = self.user_meta_classifier.fit()
        print("UserMetadataSpamClassifier Metircs:\n", model_metrics)

    def handle_predict_user(self):
        user_ids = self.user_meta_classifier.predict()
        print("UserMetadataSpamClassifier predicted users:\n", user_ids)

    def handle_train_text(self):
        model_metrics = self.text_classifier.fit()
        print("TextSpamClassifier Metircs:\n", model_metrics)

    def handle_predict_text(self):
        user_ids = self.text_classifier.predict()
        print("TextSpamClassifier predicted users:\n", user_ids)

    def handle(self, *args, **options):
        if options["exe"]:
            action = "exe"
        elif options["get_model_metrics"]:
            action = "get_model_metrics"
        elif options["load_labels"]:
            action = "load_labels"
        elif options["train_user"]:
            action = "train_user"
        elif options["predict_user"]:
            action = "predict_user"
        elif options["train_text"]:
            action = "train_text"
        elif options["predict_text"]:
            action = "predict_text"

        getattr(self, f"handle_{action}")()
