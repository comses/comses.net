import pandas as pd
import re
import sys
from django.db.models import Q
from curator.models import UserSpamStatus
from django.conf import settings

DATASET_FILE_PATH = settings.SPAM_TRAINING_DATASET_PATH


class UserSpamStatusProcessor:
    """
    UserSpamStatusProcessor
    converts UserSpamStatus querysets into Pandas dataframes.
    The functions are called by SpamClassifier variants.
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
                # It is safe to set None as 0 because:
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
                        UserSpamStatus.objects.exclude(
                            member_profile__user_id=None
                        ).values(*self.db_column_names)
                    )
                )
            )
        )

    def get_labelled_by_curator_df(self):
        return self.__rename_columns(
            self.__convert_df_markup_to_string(
                pd.DataFrame(
                    list(
                        UserSpamStatus.objects.exclude(
                            Q(member_profile__user_id=None)
                            | Q(labelled_by_curator=None)
                        ).values(*self.db_column_names)
                    )
                )
            )
        )

    # Currently not using
    # def get_unlabelled_by_curator_df(self):
    #     # return : DataFrame of user data that haven't been labeled by curator
    #     return self.__rename_columns(
    #         self.__convert_df_markup_to_string(
    #             pd.DataFrame(
    #                 list(
    #                     UserSpamStatus.objects
    #                     .exclude(member_profile__user_id=None)
    #                     .filter(labelled_by_curator=None)
    #                     .values(*self.db_column_names)
    #                 )
    #             )
    #         )
    #     )

    # Currently not using
    # def get_untrained_df(self):
    #     # return : DataFrame of user data that haven't been used for train previously
    #     return self.__rename_columns(
    #         self.__convert_df_markup_to_string(
    #             pd.DataFrame(
    #                 list(
    #                     UserSpamStatus.objects
    #                     .exclude(Q(member_profile__user_id=None) | Q(labelled_by_curator=None))
    #                     .filter(is_training_data=False)
    #                     .values(*self.db_column_names)
    #                 )
    #             )
    #         )
    #     )

    # def get_unlabelled_users(self):
    #     unlabelled_users = list(
    #         UserSpamStatus.objects.filter(
    #             Q(labelled_by_curator=None)
    #             & Q(labelled_by_text_classifier=None)
    #             & Q(labelled_by_user_classifier=None)
    #         )
    #     )
    #     return unlabelled_users

    # TODO: tune confidence threshold later
    def get_spam_users(self, confidence_threshold=0.5):
        """
        This functions will first filter out the users with labelled_by_curator==True,
        but the ones with None, only get users with labelled_by_user_classifier==True
        or labelled_by_text_classifier==True with a specific confidence level.
        """
        spam_users = list(
            UserSpamStatus.objects.filter(
                Q(labelled_by_curator=True)
                | Q(labelled_by_text_classifier=True)
                & Q(text_classifier_confidence__gte=confidence_threshold)
                | Q(labelled_by_user_classifier=True)
                & Q(user_classifier_confidence__gte=confidence_threshold)
            ).values_list("member_profile__user_id", flat=True)
        )
        return spam_users  # returns list of spam user_id

    def labelled_by_curator_exist(self):
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
        print("Loading labels CSV...")
        try:
            label_df = pd.read_csv(filepath)
        except Exception:
            print("Could not open/read file:", filepath)
            print("Please locate a dataset with labels at the path of ./curator/spam_dataset.csv")
            sys.exit()
        
        # Use when batch updating of labelled_by_curator is ready
        # spam_user_ids = label_df[label_df['is_spam']==1]['user_id'].values
        # ham_user_ids = label_df[label_df['is_spam']==0]['user_id'].values

        # is_spam = True
        # flag = self.update_labelled_by_curator(spam_user_ids, is_spam)
        # if flag == 1:
        #     user_id_list.append(spam_user_ids)

        # is_spam = False
        # flag = self.update_labelled_by_curator(ham_user_ids, is_spam)
        # if flag == 1:
        #     user_id_list.append(ham_user_ids)
            
        user_id_list = []
        for idx, row in label_df.iterrows():
            flag = self.update_labelled_by_curator(row["user_id"], bool(row["is_spam"]))
            if flag == 1:
                user_id_list.append(row["user_id"])
        print("Successfully loaded labels from CSV!")
        print("Number of user ids whose label was loaded: ", len(user_id_list))
        return user_id_list

    def update_labelled_by_curator(self, user_id, label): #TODO update with batch
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
