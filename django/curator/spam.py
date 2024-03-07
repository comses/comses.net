import json
import os
import sys

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
        """
        self.processor = UserSpamStatusProcessor()
        self.usermeta_classifier = UserMetadataSpamClassifier()
        self.text_classifier = TextSpamClassifier()
        if not self.processor.labelled_by_curator_exist():
            self.processor.load_labels_from_csv()


    def _check_model_instance_files(self):
        # Check whether UserMetadataSpamClassifier model file exists
        try:
            json_file = open(self.usermeta_classifier.MODEL_METRICS_FILE_PATH)
        except OSError:
            print("Could not open/read file:", self.usermeta_classifier.MODEL_METRICS_FILE_PATH)
            print("Please run fit_classifiers() to create model instance and metrics files.")
            sys.exit()
        with json_file:
            self.usermeta_classifier_metrics = json.load(json_file)
        
        try:
            json_file = open(self.text_classifier.MODEL_METRICS_FILE_PATH)
        except OSError:
            print("Could not open/read file:", self.text_classifier.MODEL_METRICS_FILE_PATH)
            print("Please run fit_classifiers() to create model instance and metrics files.")
            sys.exit()
        with json_file:
            self.text_classifier_metrics = json.load(json_file)


    def predict(self):
        """
        A default function to obtain the list of spam users and the metrics of the models used to
        obtain the predictions.

        Execution Steps:
            1. Call predict() of the classifier classes. This function will store the result in DB at the end.
            2. Print resluts
            4. Return the detection results stored in DB.
        """
        print("Executing spam dectection...")
        self._check_model_instance_files()

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
        self._print_model_metrics_usermeta(self.usermeta_classifier_metrics)
        self._print_model_metrics_text(self.text_classifier_metrics)

        # 4. Return spam user_ids and metrics of the model
        return result

    def get_model_metrics(self):
        """
        A function retrieves the model metrics used for spam detection. __init__() makes sure that
        the models and the model metrics files exist; therefore, the role of this function is to
        load the JSON metrics files as dictionary and return it.

        Execution Steps:
            1. Load the model metrics files from the saving directory
            2. Print the metrics
            3. Return a dictionary of the scores of existing machine learning model instances.
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
        # 1. Load the model metrics files from the saving directory
        print("Loading model metric files...")
        self._check_model_instance_files()

        print("Successfully loaded model metrics!")
        result = {
            "usermeta_spam_classifier": self.usermeta_classifier_metrics,
            "text_spam_classifier": self.text_classifier_metrics,
        }

        # 2. Print the model metrics
        self._print_model_metrics_usermeta(self.usermeta_classifier_metrics)
        self._print_model_metrics_text(self.text_classifier_metrics)

        # 3. Return a dictionary of the scores of existing machine learning model instances.
        return result


    def fit_classifiers(self):
        self.fit_usermeta_spam_classifier()
        self.fit_text_spam_classifier()


    def fit_usermeta_spam_classifier(self):
        """
        This function is a wrapper of the fit() function in UserMetadataSpamClassifier.
        It prints the model details returned by fit().

        Execution Steps:
            1. call fit() in UserMetadataSpamClassifier
            2. print the model metrics and the user_ids of the users used to calculate the scores.
        """
        model_metrics = self.usermeta_classifier.fit()
        self._print_model_metrics_usermeta(model_metrics)

    def fit_text_spam_classifier(self):
        """
        This function is a wrapper of the fit() function in TextSpamClassifier.
        It prints the model details returned by fit().

        Execution Steps:
            1. call fit() in TextSpamClassifier
            2. print the model metrics and the user_ids of the users used to calculate the scores.
        """
        model_metrics = self.text_classifier.fit()
        self._print_model_metrics_text(model_metrics)

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
            result_filepath = (
                "/shared/curator/spam/user_meta_classifier_prediction.json"
            )
            result = {
                "spam_user_ids": spam_user_ids,
                "evaluated_user_ids": evaluated_user_ids,
            }
            self._save_prediction_result(result_filepath, result)
            print("\n------------------------------------")
            print(
                "Number of spam users detected by UserMetadataSpamClassifier: %d / %d"
                % (len(spam_user_ids), len(evaluated_user_ids))
            )
            print(
                "You can find the list of ids of the detected spams and evaluated users"
            )

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
            result_filepath = "/shared/curator/spam/text_classifier_prediction.json"
            result = {
                "spam_user_ids": spam_user_ids,
                "evaluated_user_ids": evaluated_user_ids,
            }
            self._save_prediction_result(result_filepath, result)
            print("\n------------------------------------")
            print(
                "Number of spam users detected by TextSpamClassifier: %d / %d"
                % (len(spam_user_ids), len(evaluated_user_ids))
            )
            print(
                "You can find the list of ids of the detected spams and evaluated users"
            )

    def _save_prediction_result(self, filepath, data: dict):
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)

    def _print_model_metrics_usermeta(self, result: dict):
        metadata_model_tested_ids = result["test_user_ids"]
        result.pop("test_user_ids")
        metadata_model_metrics = result
        print("\n------------------------------------")
        print(
            "UserMetadataSpamClassifier Metrics :\n",
            metadata_model_metrics,
        )
        print(
            "Metrics was calculated based on a test dataset of size ",
            len(metadata_model_tested_ids),
        )
        print(
            "Here's some of the user IDs in the test dataset.\n",
            metadata_model_tested_ids[:10],
        )
        print(
            "You can find the rest in /shared/curator/spam/user_meta_classifier_metrics.json"
        )

    def _print_model_metrics_text(self, result: dict):
        text_model_tested_ids = result["test_user_ids"]
        result.pop("test_user_ids")
        text_model_metrics = result
        print("\n------------------------------------")
        print(
            "TextSpamClassifier Metrics :\n",
            text_model_metrics,
        )
        print(
            "Metrics was calculated based on a test dataset of size ",
            len(text_model_tested_ids),
        )
        print(
            "Here's some of the user IDs in the test dataset.\n",
            text_model_tested_ids[:10],
        )
        print(
            "You can find the rest in /shared/curator/spam/text_classifier_metrics.json"
        )
