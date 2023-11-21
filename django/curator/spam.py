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
        This function makes sure that both models, UserMetadataSpamClassifier and TextSpamClassifier,
        exist and saved in a saving directory for the later use. If the model instance files do not exist in
        the directory, this function calls fit() to train the models and create the files.

        SpamDetection Initialization Steps:
        1. Initializes UserSpamStatusProcessor and the classifier classes
        2. If no data has been labelled by a curator, load datase.csv
        3. If no model pickle file is found, call fit() of Classifier classes
            - if all users have None in labelled_by_curator, load to DB by calling Pipeline.load_labels_from_csv()
            - additionally, if no labels file, throw exception
        """
        self.processor = UserSpamStatusProcessor()
        self.usermeta_classifier = UserMetadataSpamClassifier()
        self.text_classifier = TextSpamClassifier()
        if not self.processor.labelled_by_curator_exist():
            self.processor.load_labels_from_csv()

        # Check whether UserMetadataSpamClassifier model file exists
        if os.path.exists(self.usermeta_classifier.MODEL_METRICS_FILE_PATH):
            with open(self.usermeta_classifier.MODEL_METRICS_FILE_PATH) as json_file:
                self.usermeta_classifier_metrics = json.load(json_file)
        else:
            # If model metrics and instance file don't exist, call fit()
            self.usermeta_classifier_metrics = self.usermeta_classifier.fit()

        # Check whether TextSpamClassifier model file exists
        if os.path.exists(self.text_classifier.MODEL_METRICS_FILE_PATH):
            with open(self.text_classifier.MODEL_METRICS_FILE_PATH) as json_file:
                self.text_classifier_metrics = json.load(json_file)
        else:
            # If model metrics and instance file don't exist, call fit()
            self.text_classifier_metrics = self.text_classifier.fit()

    def execute(self):
        """
        A default function to obtain the list of spam users and the metrics of the models used to
        obtain the predictions.

        Execution Steps:
            1. Check if there exists user data that should be labelled by the classifier models
            2. If there exists, class predict() of the classifier classes. This function will store the result in DB at the end.
            3. Print resluts
            4. Return the detection results stored in DB.
        """
        print("Executing spam dectection...")
        # 1. Check DB for unlabelled users (None in all labelled_by_curator, labelled_by_user_classifier, and labelled_by_text_classifier)
        if len(self.processor.get_unlabelled_users()) != 0:
            # 2. if there are some unlabelled users, predict
            print("Models are making predictions...")
            self.usermeta_classifier.predict()
            self.text_classifier.predict()
            print("Successfully made predictions!")

        result = {
            "spam_users": self.processor.get_spam_users(),
            "usermeta_spam_classifier": self.usermeta_classifier_metrics,
            "text_spam_classifier": self.text_classifier_metrics,
        }

        # 3. Print resluts
        metadata_model_tested_ids = result["usermeta_spam_classifier"]["test_user_ids"]
        result["usermeta_spam_classifier"].pop("test_user_ids")
        metadata_model_metrics = result["usermeta_spam_classifier"]

        text_model_tested_ids = result["text_spam_classifier"]["test_user_ids"]
        result["text_spam_classifier"].pop("test_user_ids")
        text_model_metrics = result["text_spam_classifier"]

        print("IDs of Detected Spam User :\n", result["spam_users"])
        print("\n------------------------------------\n")
        print(
            "UserMetadataSpamClassifier Metrics :\n",
            metadata_model_metrics,
        )
        print(
            "Metrics was calculated based on users with following IDs ....\n",
            metadata_model_tested_ids,
        )
        print("\n------------------------------------\n")
        print(
            "TextSpamClassifier Metrics :\n",
            text_model_metrics,
        )
        print(
            "Metrics was calculated based on users with following IDs ....\n",
            text_model_tested_ids,
        )
        # 4. Return spam user_ids and metrics of the model
        return result

    def get_model_metrics(self):
        """
        A function retrieves the model metrics used for spam detection. __init__() makes sure that
        the models and the model metrics files exist; therefore, the role of this function is to
        load the JSON metrics files as dictionary and return it.

        Execution Steps:
            1. load the model metrics files from the saving directory
            2. print the metrics
            3. return a dictionary of the scores of existing machine learning model instances.
        return:
            {   "usermeta_spam_classifier": {"Accuracy": float,
                                                  "Precision": float,
                                                  "Recall": float,
                                                  "F1",float,
                                                  "test_user_ids": list of user_id of
                                                  which users was used to calculate metrics}
                "text_spam_classifier": { same as above }
            }
        """
        print("Loading model metric files...")
        # We can assume that model and model metrics files exist after __init__
        with open(self.usermeta_classifier.MODEL_METRICS_FILE_PATH) as json_file:
            self.usermeta_classifier_metrics = json.load(json_file)

        with open(self.text_classifier.MODEL_METRICS_FILE_PATH) as json_file:
            self.text_classifier_metrics = json.load(json_file)

        print("Successfully loaded model metrics!")
        result = {
            "usermeta_spam_classifier": self.usermeta_classifier_metrics,
            "text_spam_classifier": self.text_classifier_metrics,
        }

        # Print the model metrics
        metadata_model_tested_ids = result["usermeta_spam_classifier"]["test_user_ids"]
        result["usermeta_spam_classifier"].pop("test_user_ids")
        metadata_model_metrics = result["usermeta_spam_classifier"]

        text_model_tested_ids = result["text_spam_classifier"]["test_user_ids"]
        result["text_spam_classifier"].pop("test_user_ids")
        text_model_metrics = result["text_spam_classifier"]

        print("\n------------------------------------\n")
        print(
            "UserMetadataSpamClassifier Metrics :\n",
            metadata_model_metrics,
        )
        print(
            "Metrics was calculated based on users with following IDs ....\n",
            metadata_model_tested_ids,
        )
        print("\n------------------------------------\n")
        print(
            "TextSpamClassifier Metrics :\n",
            text_model_metrics,
        )
        print(
            "Metrics was calculated based on users with following IDs ....\n",
            text_model_tested_ids,
        )
        return result

    def fit_usermeta_spam_classifier(self):
        """
        This function is a wrapper of the fit() function in UserMetadataSpamClassifier.
        It prints the model details returned by fit().

        Execution Steps:
            1. call fit() in UserMetadataSpamClassifier
            2. print the model metrics and the user_ids of the users used to calculate the scores.
        """
        model_metrics = self.usermeta_classifier.fit()
        metadata_model_tested_ids = model_metrics["test_user_ids"]
        model_metrics.pop("test_user_ids")
        metadata_model_metrics = model_metrics
        print("\n------------------------------------\n")
        print(
            "UserMetadataSpamClassifier Metrics :\n",
            metadata_model_metrics,
        )
        print(
            "Metrics was calculated based on users with following IDs ....\n",
            metadata_model_tested_ids,
        )

    def fit_text_spam_classifier(self):
        """
        This function is a wrapper of the fit() function in TextSpamClassifier.
        It prints the model details returned by fit().

        Execution Steps:
            1. call fit() in TextSpamClassifier
            2. print the model metrics and the user_ids of the users used to calculate the scores.
        """
        model_metrics = self.text_classifier.fit()
        text_model_tested_ids = model_metrics["test_user_ids"]
        model_metrics.pop("test_user_ids")
        text_model_metrics = model_metrics
        print("\n------------------------------------\n")
        print(
            "TextSpamClassifier Metrics :\n",
            text_model_metrics,
        )
        print(
            "Metrics was calculated based on users with following IDs ....\n",
            text_model_tested_ids,
        )

    def predict_usermeta_spam_classifier(self):
        """
        This function is a wrapper of the predict() function in UserMetadataSpamClassifier.
        It prints the model details returned by predict().

        Execution Steps:
            1. call predict() in UserMetadataSpamClassifier
            2. Print the evaluated users and users that were detected as a spam.
        """
        evaluated_user_ids, spam_user_ids = self.usermeta_classifier.predict()
        if len(evaluated_user_ids) == 0:
            print(
                "Since all users were labelled by curator, classifier prediction was not executed.\n"
            )
        else:
            print("UserMetadataSpamClassifier evaluated users:\n", evaluated_user_ids)
            print("Spam Users :\n", spam_user_ids)

    def predict_text_spam_classifier(self):
        """
        This function is a wrapper of the predict() function in TextSpamClassifier.
        It prints the model details returned by predict().

        Execution Steps:
            1. call predict() in TextSpamClassifier
            2. Print the evaluated users and users that were detected as a spam.
        """
        evaluated_user_ids, spam_user_ids = self.text_classifier.predict()

        if len(evaluated_user_ids) == 0:
            print(
                "Since all users were labelled by curator, classifier prediction was not executed.\n"
            )
        else:
            print("TextSpamClassifier evaluated users:\n", evaluated_user_ids)
            print("Spam Users :\n", spam_user_ids)
