import pandas as pd
import numpy as np
import re
import json
import os
from django.contrib.auth.models import User
from django.db.models import Q
from itertools import chain
import warnings
from datetime import datetime, timedelta, date

from curator.models import UserSpamStatus
from curator.spam_detection_models import UserMetadataSpamClassifier, TextSpamClassifier

warnings.filterwarnings("ignore")  # ignore warnings
SPAM_DIR_PATH = "shared/curator/spam/"
DATASET_FILE_PATH = "/code/curator/dataset.csv"


class SpamDetection:
    """
    This class servers as an API for the spam detection features. Calling execute() returns the spam users detected
    in the DB as well as the scores of the machine leaning models used to detect the spams.
    """

    def __init__(self):
        """
        SpamDetection Initialization Steps
        1. Initializes UserSpamStatusProcessor and the classidier classes
        2. If no data has been labelled by a curator, load datase.csv
        3. If no model pickle file is found, call fit() of Classifier classes
            - if all users have None in labelled_by_curator, load to DB by calling Pipeline.load_labels_from_csv()
            - additionally, if no labels file, throw exception
        """
        self.processor = UserSpamStatusProcessor()
        self.user_meta_classifier = UserMetadataSpamClassifier()
        self.text_classifier = TextSpamClassifier()
        if not self.processor.have_labelled_by_curator():
            self.processor.load_labels_from_csv()

        # Check whether UserMetadataSpamClassifier model file exists
        if os.path.exists(self.user_meta_classifier.MODEL_METRICS_FILE_PATH):
            with open(self.user_meta_classifier.MODEL_METRICS_FILE_PATH) as json_file:
                self.user_meta_classifier_metrics = json.load(json_file)
        else:
            self.user_meta_classifier_metrics = self.user_meta_classifier.fit()

        # TODO: remove commnet out after TextSpamClassifier() is fixed
        # Check whether TextSpamClassifier model file exists
        # if os.path.exists(self.text_classifier.MODEL_METRICS_FILE_PATH):
        #     with open(self.text_classifier.MODEL_METRICS_FILE_PATH) as json_file:
        #         self.text_classifier_metrics = json.load(json_file)
        # else:
        #     self.text_classifier.fit()
        # self.text_classifier_metrics = self.text_classifier.fit()

        self.text_classifier_metrics = {}

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
            self.user_meta_classifier.predict()
            # self.text_classifier.predict() TODO: remove commnet out after TextSpamClassifier() is fixed

        # 3. Return spam user_ids and metrics of the model
        return {
            "spam_users": self.processor.get_spam_users(),
            "user_metadata_spam_classifier": self.user_meta_classifier_metrics,
            "text_spam_classifier": self.text_classifier_metrics,
        }

    def refine(self):
        """
        Retrain machine learning models using new data in DB
        return : a dictionary of the models scores after retraining.
        """
        self.user_meta_classifier_metrics = self.user_meta_classifier.partial_fit()
        # self.text_classifier_metrics = self.text_classifier.fit() TODO: remove commnet out after TextSpamClassifier() is fixed
        return {
            "user_metadata_spam_classifier": self.user_meta_classifier_metrics,
            "text_spam_classifier": self.text_classifier_metrics,
        }

    def get_model_metrics(self):
        """
        return: a dictionary of the scores of existing machine learning model instances.
        """

        # We can assume that model and model metrics files exist after __init__
        with open(self.user_meta_classifier.MODEL_METRICS_FILE_PATH) as json_file:
            self.user_meta_classifier_metrics = json.load(json_file)

        # TODO: remove commnet out after TextSpamClassifier() is fixed
        # with open(self.text_classifier.MODEL_METRICS_FILE_PATH) as json_file:
        #     self.text_classifier_metrics = json.load(json_file)

        return {
            "user_metadata_spam_classifier": self.user_meta_classifier_metrics,
            "text_spam_classifier": self.text_classifier_metrics,
        }


class UserSpamStatusProcessor:
    """
    UserSpamStatusProcessor
    converts UserSpamStatus querysets into Pandas dataframes
    """

    def __init__(self):
        self.db_column_names = [
            "member_profile__user_id",
            "member_profile__user__first_name",
            "member_profile__user__last_name",
            "member_profile__user__is_active",
            "member_profile__user__email",
            "member_profile__timezone",
            "member_profile__affiliations",
            "member_profile__bio",
            "member_profile__research_interests",
            "member_profile__personal_url",
            "member_profile__professional_url",
            "labelled_by_curator",
            "labelled_by_text_classifier",
            "labelled_by_user_classifier",
            "text_classifier_confidence",
            "user_classifier_confidence",
        ]

        self.column_names = [
            "user_id",
            "first_name",
            "last_name",
            "is_active",
            "email",
            "timezone",
            "affiliations",
            "bio",
            "research_interests",
            "personal_url",
            "professional_url",
        ]

        self.type_int_bool_column_names = [
            "member_profile__user_id",
            "labelled_by_curator",
            # "labelled_by_text_classifier",
            # "labelled_by_user_classifier",
            # "text_classifier_confidence",
            # "user_classifier_confidence",
        ]

    def __rename_columns(self, df):
        if df.empty:
            return df
        df.rename(
            columns={
                self.db_column_names[0]: self.column_names[0],
                self.db_column_names[1]: self.column_names[1],
                self.db_column_names[2]: self.column_names[2],
                self.db_column_names[3]: self.column_names[3],
                self.db_column_names[4]: self.column_names[4],
                self.db_column_names[5]: self.column_names[5],
                self.db_column_names[6]: self.column_names[6],
                self.db_column_names[7]: self.column_names[7],
                self.db_column_names[8]: self.column_names[8],
                self.db_column_names[9]: self.column_names[9],
                self.db_column_names[10]: self.column_names[10],
            },
            inplace=True,
        )
        return df

    def __convert_df_markup_to_string(self, df):
        if df.empty:
            return df
        for col in df.columns:
            if col in self.type_int_bool_column_names:
                df[col] = df[col].fillna(0).astype(int)
                # It is safe to set Nan as 0 because:
                # for training, all values with labelled_by_curator=None are exclueded before passed to this function.
                # for prediction, the labelled_by_curator column is not used during prediction process.
            else:
                df[col] = df[col].apply(
                    lambda text: re.sub(r"<.*?>", " ", str(text))
                )  # Removing markdown
        return df

    def get_all_users_df(self):
        return self.__rename_columns(
            self.__convert_df_markup_to_string(
                pd.DataFrame(
                    list(
                        UserSpamStatus.objects.all()
                        .exclude(member_profile__user_id=None, labelled_by_curator=None)
                        .values(*self.db_column_names)
                    )
                )
            )
        )

    def get_unlabelled_by_curator_df(self):
        # return : DataFrame of user data that haven't been labeled by curator
        return self.__rename_columns(
            self.__convert_df_markup_to_string(
                pd.DataFrame(
                    list(
                        UserSpamStatus.objects.all()
                        .exclude(member_profile__user_id=None)
                        .filter(labelled_by_curator=None)
                        .values(*self.db_column_names)
                    )
                )
            )
        )

    def get_untrained_df(self):
        # return : DataFrame of user data that haven't been used for train previously
        return self.__rename_columns(
            self.__convert_df_markup_to_string(
                pd.DataFrame(
                    list(
                        UserSpamStatus.objects.all()
                        .exclude(member_profile__user_id=None, labelled_by_curator=None)
                        .filter(is_training_data=False)
                        .values(*self.db_column_names)
                    )
                )
            )
        )

    def get_unlabelled_users(self):
        unlabelled_users = list(
            UserSpamStatus.objects.filter(
                Q(labelled_by_curator=None)
                & Q(labelled_by_text_classifier=None)
                & Q(labelled_by_user_classifier=None)
            )
        )
        return unlabelled_users

    # FIXME: tune confidence threshold later
    def get_spam_users(self, confidence_threshold=0.5):
        """
        This functions will first filter out the users with labelled_by_curator==True,
        but the ones with None, only get users with labelled_by_user_classifier == True
        or labelled_by_text_classifier == True with a specific confidence level.
        """
        spam_users = list(
            UserSpamStatus.objects.filter(
                Q(labelled_by_curator=True)
                | Q(labelled_by_text_classifier=True)
                & Q(text_classifier_confidence__gte=confidence_threshold)
                | Q(labelled_by_user_classifier=True)
                & Q(user_classifier_confidence__gte=confidence_threshold)
            )
        )
        return spam_users

    def have_labelled_by_curator(self):
        # if there are users with labelled_by_curator != None, return True
        if UserSpamStatus.objects.filter(
            Q(labelled_by_curator=True) | Q(labelled_by_curator=False)
        ).exists():
            return True
        return False

    def all_have_labels(self):
        # if all users have any kind of labels (labelled_by_curator, user_meta_classifier, text_classifier), return True
        if UserSpamStatus.objects.filter(
            Q(member_profile__user_id=None)
            & Q(labelled_by_curator=None)
            & Q(labelled_by_user_classifier=None)
            & Q(labelled_by_text_classifier=None)
        ).exists():
            return False  # Haven't labelled by either a curator or the models
        return True

    def load_labels_from_csv(self, filepath=DATASET_FILE_PATH):
        """
        This function updates "labelled_by_curator" field of the SpamRecommendation table bsed on external dataset file.
        Dataset should have columns named "user_id" and "is_spam"
        param : filepath of dataset to be loaded
        return : list of user_ids which labelled_by_curator was updated
        """
        label_df = pd.read_csv(filepath)  # TODO add exception
        user_id_list = []
        for idx, row in label_df.iterrows():
            flag = self.update_labelled_by_curator(row["user_id"], bool(row["is_spam"]))
            if flag == 1:
                user_id_list.append(row["user_id"])
        return user_id_list

    def update_labelled_by_curator(self, user_id, label):
        return UserSpamStatus.objects.filter(member_profile__user_id=user_id).update(
            labelled_by_curator=label
        )  # return 0(fail) or 1(success)

    def update_training_data(self, df, training_data=True):
        # param : DataFrame of user_ids (int) that were used to train a model
        # return : None
        for idx, row in df.iterrows():
            UserSpamStatus.objects.filter(
                member_profile__user_id=row["user_id"]
            ).update(is_training_data=training_data)

    def update_predictions(self, prediction_df, isTextClassifier=False):
        # params : prediction_df ... a Dataframe with columns "user_id", "labelled_by_{}", and "{}_classifier_confidence"
        # return : None
        if isTextClassifier:
            for idx, row in prediction_df.iterrows():
                UserSpamStatus.objects.filter(
                    member_profile__user_id=row.user_id
                ).update(
                    labelled_by_text_classifier=row.labelled_by_text_classifier,
                    text_classifier_confidence=row.text_classifier_confidence,
                )
        else:
            for idx, row in prediction_df.iterrows():
                UserSpamStatus.objects.filter(
                    member_profile__user_id=row.user_id
                ).update(
                    labelled_by_user_classifier=row.labelled_by_user_classifier,
                    user_classifier_confidence=row.user_classifier_confidence,
                )
