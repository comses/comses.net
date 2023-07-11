import logging
import pathlib

from django.core.management.base import BaseCommand

from curator.spam import DATASET_FILE_PATH
from curator.spam_detection_models import SpamDetection

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Perform spam detection"

    def __init__(self):
        self.detection = SpamDetection()
        self.processor = self.detection.processor
        self.user_meta_classifier = self.detection.user_meta_classifier
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
            "--refine",
            "-r",
            action="store_true",
            default=False,
            help="retrain models and returns refined model metrics",
        )
        parser.add_argument(
            "--get_model_metrics",
            "-g",
            action="store_true",
            default=False,
            help="retrain model accuracy, precision, recall and f1 scores",
        )
        parser.add_argument(
            "--load_labels",
            "-l",
            action="store_true",
            default=False,
            help="save initial dataset to the DB. ",
        )
        parser.add_argument("--train_user", "-tu", action="store_true", default=False)
        parser.add_argument(
            "--p_train_user",
            "-ptu",
            action="store_true",
            default=False,
            help="perform partial train on data with no ML model recomendation",
        )
        parser.add_argument("--predict_user", "-pu", action="store_true", default=False)
        parser.add_argument("--train_text", "-tb", action="store_true", default=False)
        parser.add_argument("--predict_text", "-pb", action="store_true", default=False)

    def handle_exe(self):
        spam_users, user_model_metircs, text_model_metrics = self.detection.execute()
        # print(spam_users)
        # print(user_model_metircs)
        # print(text_model_metrics)

    def handle_refine(self):
        user_model_metircs, text_model_metrics = self.detection.refine()
        print(user_model_metircs)
        print(text_model_metrics)

    def handle_get_model_metrics(self):
        metrics = self.detection.get_model_metrics()
        print(metrics)

    def handle_load_labels(self, load_directory):
        self.processor.update_labels(load_directory)

    def handle_train_user(self):
        self.user_meta_classifier.fit()

    def handle_predict_user(self):
        self.user_meta_classifier.predict()

    def handle_p_train_user(self):
        self.user_meta_classifier.partial_fit()

    def handle_train_text(self):
        self.text_classifier.fit()

    def handle_predict_text(self):
        self.text_classifier.predict()

    def handle(self, *args, **options):
        exe = options["exe"]
        refine = options["refine"]
        model_metrics = options["get_model_metrics"]
        load = options["load_labels"]
        train_user = options["train_user"]
        predict_user = options["predict_user"]
        p_train_user = options["p_train_user"]
        train_text = options["train_text"]
        predict_text = options["predict_text"]

        load_directory = pathlib.Path(DATASET_FILE_PATH)

        if exe:
            self.handle_exe()
        elif refine:
            self.handle_refine()
        elif model_metrics:
            self.handle_get_model_metrics()
        elif load:
            self.handle_load_labels(load_directory)
        elif train_user:
            self.handle_train_user()
        elif predict_user:
            self.handle_predict_user()
        elif p_train_user:
            self.handle_p_train_user()
        elif train_text:
            self.handle_train_text()
        elif predict_text:
            self.handle_predict_text()
