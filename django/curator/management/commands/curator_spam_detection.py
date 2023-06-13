import logging
import pathlib

from django.core.management.base import BaseCommand

from curator.models import TagCleanup, PENDING_TAG_CLEANUPS_FILENAME
# from curator.spam_detection_models import SpamClassifier
from curator.spam_detect import UserPipeline
from curator.spam_detection_model import SpamClassifier

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Perform spam detection"
    pipeline = UserPipeline()
    def add_arguments(self, parser):
        parser.add_argument("--init_table", "-i", action="store_true", default=False, help="initialize SpamRecommendation table. ")
        parser.add_argument("--load", "-l", action="store_true", default=False, help="save initial dataset to the DB (SpamRecommendation table). ")
        parser.add_argument("--train", "-t", action="store_true", default=False)
        parser.add_argument("--predict", "-i", action="store_true", default=False)
        parser.add_argument("--p_train", "-p", action="store_true", default=False, help="perform partial train on data with no ML model recomendation")

    def handle_init_table(self):
        pipeline = UserPipeline()
        pipeline.initalize_SpamRecommendation()

    def handle_load(self, load_directory):
        pipeline = UserPipeline()
        pipeline.load_labels(load_directory)

    def handle_train(self):
        classifier = SpamClassifier()
        classifier.train()

    def handle_predict(self):
        classifier = SpamClassifier()
        classifier.predict()

    def handle_p_train(self):
        classifier = SpamClassifier()
        classifier.partial_train()

    def handle(self, *args, **options):
        init_table = options["init_table"]
        load = options["load"]
        train = options["train"]
        predict = options["predict"]
        p_train = options["p_train"]

        # load_directory = pathlib.Path("/shared/incoming/curator/tags")
        load_directory = pathlib.Path("/shared/curator/dataset.csv") #TODO check for the right place to store files
        
        if init_table:
            self.handle_init_table()
        if load:
            self.handle_load(load_directory)
        elif train:
            self.handle_train()
        elif predict:
            self.handle_predict()
        elif p_train:
            self.handle_p_train()


