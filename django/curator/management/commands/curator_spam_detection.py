import logging
import pathlib

from django.core.management.base import BaseCommand

from curator.models import TagCleanup, PENDING_TAG_CLEANUPS_FILENAME
# from curator.spam_detection_models import SpamClassifier
from curator.spam_detect import UserPipeline
from curator.spam_detection_model import SpamClassifier, BioSpamClassifier

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Perform spam detection"
    pipeline = UserPipeline()
    def add_arguments(self, parser):
        # parser.add_argument("--init_table", "-i", action="store_true", default=False, help="initialize SpamRecommendation table. ")
        parser.add_argument("--load_user_labels", "-l", action="store_true", default=False, help="save initial dataset to the DB (SpamRecommendation table). ")
        parser.add_argument("--train_user", "-tu", action="store_true", default=False)
        parser.add_argument("--p_train_user", "-ptu", action="store_true", default=False, help="perform partial train on data with no ML model recomendation")
        parser.add_argument("--predict_user", "-pu", action="store_true", default=False)
        parser.add_argument("--load_bio", "-lb", action="store_true", default=False)
        parser.add_argument("--train_bio", "-tb", action="store_true", default=False)
        parser.add_argument("--predict_bio", "-pb", action="store_true", default=False)

    def handle_load_user_labels(self, load_directory):
        pipeline = UserPipeline()
        pipeline.load_labels(load_directory)

    def handle_train_user(self):
        classifier = SpamClassifier()
        classifier.fit()

    def handle_predict_user(self):
        classifier = SpamClassifier()
        classifier.predict()

    def handle_p_train_user(self):
        classifier = SpamClassifier()
        classifier.partial_fit()
    
    def handle_load_bio(self):
        classifier = BioSpamClassifier()
        classifier.load_model()

    def handle_train_bio(self):
        classifier = BioSpamClassifier()
        classifier.fit_on_curator_labelled_recommendations()

    def handle_predict_bio(self):
        classifier = BioSpamClassifier()
        classifier.predict_all_unlabelled_users()

    def handle(self, *args, **options):
        load_user = options["load_user_labels"]
        train_user = options["train_user"]
        predict_user = options["predict_user"]
        p_train_user = options["p_train_user"]
        load_bio = options["load_bio"]
        train_bio = options["train_bio"]
        predict_bio = options["predict_bio"]

        # load_directory = pathlib.Path("/shared/curator/dataset.csv")
        load_directory = pathlib.Path("dataset.csv")
        
        if load_user:
            self.handle_load_user_labels(load_directory)
        elif train_user:
            self.handle_train_user()
        elif predict_user:
            self.handle_predict_user()
        elif p_train_user:
            self.handle_p_train_user()
        elif load_bio:
            self.handle_load_bio()
        elif train_bio:
            self.handle_train_bio()
        elif predict_bio:
            self.handle_predict_bio()


