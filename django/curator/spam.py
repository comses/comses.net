import json
import os

from django.conf import settings

from .spam_processor import UserSpamStatusProcessor
from .spam_classifiers import (
    UserMetadataSpamClassifier,
    TextSpamClassifier,
)


class SpamDetector:
    """
    This class serves as an API for the spam detection features. Calling execute() returns the spam users detected
    in the DB as well as the scores of the machine leaning models used to detect the spams.
    """

    def __init__(self):
        """
        SpamDetection Initialization Steps
        1. Initializes UserSpamStatusProcessor and the classifier classes
        2. If no data has been labelled by a curator, load datase.csv
        3. If no model pickle file is found, call fit() of Classifier classes
            - if all users have None in labelled_by_curator, load to DB by calling Pipeline.load_labels_from_csv()
            - additionally, if no labels file, throw exception
        """
        settings.SPAM_DIR_PATH.mkdir(parents=True, exist_ok=True)
        self.processor = UserSpamStatusProcessor()
        self.user_metadata_classifier = UserMetadataSpamClassifier()
        self.text_classifier = TextSpamClassifier()
        if not self.processor.labelled_by_curator_exist():
            self.processor.load_labels_from_csv()

        # Check whether UserMetadataSpamClassifier model file exists
        if os.path.exists(self.user_metadata_classifier.MODEL_METRICS_FILE_PATH):
            with open(
                self.user_metadata_classifier.MODEL_METRICS_FILE_PATH
            ) as json_file:
                self.user_meta_classifier_metrics = json.load(json_file)
        else:
            # If model metrics and instance file don't exist, call fit()
            self.user_meta_classifier_metrics = self.user_meta_classifier.fit()

        # Check whether TextSpamClassifier model file exists
        if os.path.exists(self.text_classifier.MODEL_METRICS_FILE_PATH):
            with open(self.text_classifier.MODEL_METRICS_FILE_PATH) as json_file:
                self.text_classifier_metrics = json.load(json_file)
        else:
            # If model metrics and instance file don't exist, call fit()
            self.text_classifier_metrics = self.text_classifier.fit()

    def execute(self):
        """
        Execution Steps
        1. Check if there exists user data that should be labelled by the classifier models
        2. If there exists, class predict() of the classifier classes. This function will store the result in DB at the end.
        3. Return the detection results stored in DB.
        """

        # 1. Check DB for unlabelled users (None in all labelled_by_curator, labelled_by_user_classifier, and labelled_by_text_classifier)
        if len(self.processor.get_unlabelled_users()) != 0:
            # 2. if there are some unlabelled users, predict
            self.user_metadata_classifier.predict()
            self.text_classifier.predict()

        # 3. Return spam user_ids and metrics of the model
        return {
            "spam_users": self.processor.get_spam_users(),
            "user_metadata_spam_classifier": self.user_meta_classifier_metrics,
            "text_spam_classifier": self.text_classifier_metrics,
        }


    def get_model_metrics(self):
        """
        return: a dictionary of the scores of existing machine learning model instances.
        """

        # We can assume that model and model metrics files exist after __init__
        with open(self.user_metadata_classifier.MODEL_METRICS_FILE_PATH) as json_file:
            self.user_meta_classifier_metrics = json.load(json_file)

        with open(self.text_classifier.MODEL_METRICS_FILE_PATH) as json_file:
            self.text_classifier_metrics = json.load(json_file)

        return {
            "user_metadata_spam_classifier": self.user_meta_classifier_metrics,
            "text_spam_classifier": self.text_classifier_metrics,
        }
