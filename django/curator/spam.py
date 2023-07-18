import pandas as pd
import numpy as np
import re
from django.contrib.auth.models import User
from django.db.models import Q
from itertools import chain
import warnings
from datetime import datetime, timedelta, date

from curator.models import UserSpamStatus
from core.models import MemberProfile

warnings.filterwarnings("ignore")  # ignore warnings
SPAM_DIR_PATH = "/shared/curator/spam/"
DATASET_FILE_PATH = SPAM_DIR_PATH + "dataset.csv"


class UserSpamStatusProcessor:
    """
    UserSpamStatusProcessor
    converts UserSpamStatus querysets into Pandas dataframes
    """

    def __init__(self):
        self.column_names = [
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
                self.column_names[0]: "user_id",
                self.column_names[1]: "first_name",
                self.column_names[2]: "last_name",
                self.column_names[3]: "is_active",
                self.column_names[4]: "email",
                self.column_names[5]: "timezone",
                self.column_names[6]: "affiliations",
                self.column_names[7]: "bio",
                self.column_names[8]: "research_interests",
                self.column_names[9]: "personal_url",
                self.column_names[10]: "professional_url",
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
                # It is safe to set Nan as ) because:
                # for training, all values with labelled_by_curator=None are exclueded before passed to this function.
                # for prediction, labelled_by_curator column is not used during prediction process.
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
                        .exclude(member_profile__user_id=None)
                        .values(*self.column_names)
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
                        UserSpamStatus.objects.exclude(member_profile__user_id=None)
                        .filter(labelled_by_curator=None)
                        .values(*self.column_names)
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
                        UserSpamStatus.objects.exclude(
                            member_profile__user_id=None, labelled_by_curator=None
                        )
                        .filter(is_training_data=False)
                        .values(*self.column_names)
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

    def update_labels(self, filepath=DATASET_FILE_PATH, check_DB=False):
        # This function updates "labelled_by_curator" field of the SpamRecommendation table bsed on external dataset file.
        # Dataset should have columns named "user_id" and "is_spam"
        # param : filepath of dataset to be loaded
        # return : None

        if (
            check_DB
            and UserSpamStatus.objects.filter(
                Q(labelled_by_curator=True) | Q(labelled_by_curator=False)
            ).exists()
        ):
            # if there are user with non-None values as labelled_by_curator, no need to load the label file
            return

        label_df = pd.read_csv(filepath)  # TODO add exception
        for idx, row in label_df.iterrows():
            UserSpamStatus.objects.filter(
                member_profile__user_id=row["user_id"]
            ).update(labelled_by_curator=bool(row["is_spam"]))

    def update_training_data(self, df):
        # param : DataFrame of user_ids (int) that were used to train a model
        # return : None
        for idx, row in df.iterrows():
            UserSpamStatus.objects.filter(
                member_profile__user_id=row["user_id"]
            ).update(is_training_data=True)

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
