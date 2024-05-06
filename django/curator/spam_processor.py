import pandas as pd
from pandas import DataFrame
import re
from ast import literal_eval
import logging
from django.db.models import Q
from curator.models import UserSpamStatus, UserSpamPrediction
from django.conf import settings
from enum import Enum
from typing import List

# from .spam import PresetContextID

DATASET_FILE_PATH = settings.SPAM_TRAINING_DATASET_PATH
logger = logging.getLogger(__name__)


class UserSpamStatusProcessor:
    """
    Convert UserSpamStatus querysets into Pandas dataframes.
    Store spam labels to UserSpamStatus and predictions to UserSpamPrediction.
    """

    def __init__(self):
        self.db_fields = [
            "member_profile__user_id",
            "member_profile__user__first_name",
            "member_profile__user__last_name",
            "member_profile__user__email",
            "member_profile__user__is_active",
            "member_profile__timezone",
            "member_profile__affiliations",
            "member_profile__bio",
            "member_profile__research_interests",
            "member_profile__personal_url",
            "member_profile__professional_url",
            "label",
        ]

        self.df_fields = [
            "user_id",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "timezone",
            "affiliations",
            "bio",
            "research_interests",
            "personal_url",
            "professional_url",
            "label",
        ]

        self.field_type = {
            "string": [
                "first_name",
                "last_name",
                "email",
                "timezone",
                "affiliations",
                "bio",
                "research_interests",
                "personal_url",
                "professional_url",
            ],
            "categorical": ["is_active"],
            "numerical": ["user_id", "label"],
        }

        self.db_df_field_mapping = {
            self.db_fields[0]: self.df_fields[0],
            self.db_fields[1]: self.df_fields[1],
            self.db_fields[2]: self.df_fields[2],
            self.db_fields[3]: self.df_fields[3],
            self.db_fields[4]: self.df_fields[4],
            self.db_fields[5]: self.df_fields[5],
            self.db_fields[6]: self.df_fields[6],
            self.db_fields[7]: self.df_fields[7],
            self.db_fields[8]: self.df_fields[8],
            self.db_fields[9]: self.df_fields[9],
            self.db_fields[10]: self.df_fields[10],
            self.db_fields[11]: self.df_fields[11],
        }

        self.df_db_field_mapping = dict(
            (v, k) for k, v in self.db_df_field_mapping.items()
        )

    def __rename_df_fields(self, df: DataFrame) -> DataFrame:
        """
        Rename fields in the DataFrame according to the mapping defined in 'db_df_field_mapping'.
        This internal method modifies the DataFrame columns in place if it is not empty.

        Params:
            df (DataFrame): The DataFrame whose columns are to be renamed.
        Returns:
            DataFrame: The DataFrame with renamed fields.
        """
        if df.empty:
            return df

        df.rename(
            columns=self.db_df_field_mapping,
            inplace=True,
        )
        return df

    def __preprocess_fields(self, df: DataFrame) -> DataFrame:
        """
        Preprocess fields in the DataFrame based on their data type as specified in 'field_type'.
        This involves filling missing values, applying transformations, and splitting or restructuring specific fields.

        Params:
            df (DataFrame): The DataFrame to preprocess.
        Returns:
            DataFrame: The preprocessed DataFrame.
        """
        if df.empty:
            return df

        for col in df.columns:
            if col in self.field_type["string"]:
                df[col] = df[col].fillna("")
                df[col] = df[col].apply(
                    lambda text: re.sub(r"<.*?>", " ", str(text))
                )  # Removing markdown
                if col == "affiliations":
                    df[col] = df[col].apply(self.__restructure_affiliation_field)
                if col == "email":
                    df = df.apply(self.__split_email_field, axis=1)
                    df = df.drop("email", axis=1)

            elif col in self.field_type["numerical"]:
                df[col] = df[col].fillna(-1).astype(int)

            elif col in self.field_type["categorical"]:
                df[col] = df[col].fillna("NaN").astype(str)

        return df

    def __split_email_field(self, row):
        """
        Split the email into username and domain and update the row accordingly.

        Params:
            row (Series): A row of the DataFrame containing the email field.
        Returns:
            Series: The updated row with 'email_username' and 'email_domain' fields.
        """
        row["email_username"], row["email_domain"] = row["email"].split("@")
        return row

    def __restructure_affiliation_field(self, array):
        """
        Restructure the 'affiliations' field into a more readable string format.

        Params:
            array (str): A string representation of a list of dictionaries describing affiliations.
        Returns:
            str: A formatted string summarizing the affiliations.
        """
        array = literal_eval(array)
        if len(array) != 0:
            result = ""
            for affili_dict in array:
                name = affili_dict["name"] if ("name" in affili_dict.keys()) else ""
                url = affili_dict["url"] if ("url" in affili_dict.keys()) else ""
                ror_id = (
                    affili_dict["ror_id"] if ("ror_id" in affili_dict.keys()) else ""
                )
                affili = name + " (" + "url: " + url + ", ror id: " + ror_id + "), "
                result = result + affili
            return result
        else:
            return ""

    def __validate_selected_fields(self, selected_fields: List[str]) -> List[str]:
        """
        Validate the selected fields against the database fields. Only fields that exist in the database are kept.

        Params:
            selected_fields (List[str]): A list of field names to validate.
        Returns:
            List[str]: A list of validated field names.
        """
        validated_fields = []
        for field in selected_fields:
            if field in self.df_fields:
                validated_fields.append(field)
        return validated_fields

    def get_all_users(self, selected_fields: List[str]) -> DataFrame:
        """
        Fetch and return all user data with the selected fields processed and renamed for easier analysis.

        Params:
            selected_fields (List[str]): Fields to be included in the returned data.
        Returns:
            DataFrame: A DataFrame containing the data for all users with the specified fields.
        """
        selected_fields = self.__validate_selected_fields(selected_fields)
        selected_fields.append("user_id")
        selected_db_fields = [self.df_db_field_mapping[v] for v in selected_fields]
        return self.__preprocess_fields(
            self.__rename_df_fields(
                DataFrame(
                    list(
                        UserSpamStatus.objects.exclude(
                            member_profile__user_id=None
                        ).values(*selected_db_fields)
                    )
                )
            )
        )

    def get_selected_users(
        self, user_ids: int, selected_fields: List[str]
    ) -> DataFrame:
        """
        Fetch and return data for specified users based on provided user IDs and selected fields.
        This function preprocesses, renames fields, and returns data specific to given user IDs.

        Params:
            user_ids (int): The user IDs to filter by.
            selected_fields (List[str]): Fields to be included in the returned data.
        Returns:
            DataFrame: A DataFrame containing the data for selected users with the specified fields.
        """
        selected_fields = self.__validate_selected_fields(selected_fields)
        selected_fields.append("user_id")
        selected_db_fields = [self.df_db_field_mapping[v] for v in selected_fields]
        return self.__preprocess_fields(
            self.__rename_df_fields(
                DataFrame(
                    list(
                        UserSpamStatus.objects.exclude(member_profile__user_id=None)
                        .filter(member_profile__user_id__in=user_ids)
                        .values(*selected_db_fields)
                    )
                )
            )
        )

    def get_all_users_with_label(self, selected_fields: List[str]) -> DataFrame:
        """
        Fetch and return data for all users who have a label, using specified fields.
        This function handles preprocessing and renaming of fields to match database schema.

        Params:
            selected_fields (List[str]): Fields to be included in the returned data.
        Returns:
            DataFrame: A DataFrame containing labeled user data with the specified fields.
        """
        selected_fields = self.__validate_selected_fields(selected_fields)
        selected_fields.extend(["label", "user_id"])
        selected_db_fields = [self.df_db_field_mapping[v] for v in selected_fields]
        return self.__preprocess_fields(
            self.__rename_df_fields(
                DataFrame(
                    list(
                        UserSpamStatus.objects.exclude(
                            Q(member_profile__user_id=None) | Q(label=None)
                        ).values(*selected_db_fields)
                    )
                )
            )
        )

    def get_selected_users_with_label(
        self, user_ids: int, selected_fields: List[str]
    ) -> DataFrame:
        """
        Fetch and return data for specified users with labels, using provided user IDs and selected fields.
        This function handles preprocessing and renaming of fields to facilitate analysis.

        Params:
            user_ids (int): The user IDs to filter by.
            selected_fields (List[str]): Fields to be included in the returned data.
        Returns:
            DataFrame: A DataFrame containing the data for selected labeled users.
        """
        selected_fields = self.__validate_selected_fields(selected_fields)
        selected_fields.extend(["label", "user_id"])
        selected_db_fields = [self.df_db_field_mapping[v] for v in selected_fields]
        return self.__preprocess_fields(
            self.__rename_df_fields(
                DataFrame(
                    list(
                        UserSpamStatus.objects.exclude(
                            Q(member_profile__user_id=None) | Q(label=None)
                        )
                        .filter(member_profile__user_id__in=user_ids)
                        .values(*selected_db_fields)
                    )
                )
            )
        )

    # TODO: tune confidence threshold later
    def get_predicted_spam_users(
        self, context_id: Enum, confidence_threshold=0.5
    ) -> List[int]:
        """
        Retrieve user IDs predicted as spam with a confidence level above the specified threshold.

        Params:
            context_id (Enum): The context identifier for the spam prediction.
            confidence_threshold (float): The confidence threshold for considering a user as spam.
        Returns:
            List[int]: A list of user IDs classified as spam above the specified confidence threshold.
        """
        spam_users = set(
            list(
                UserSpamPrediction.objects.filter(
                    Q(context_id=context_id.name)
                    & Q(prediction=True)
                    & Q(confidence__gte=confidence_threshold)
                ).values_list("spam_status__member_profile__user_id", flat=True)
            )
        )
        return spam_users  # returns list of spam user_id

    def labels_exist(self) -> bool:
        """
        Check if any user labels exist in the database.

        Returns:
            bool: True if there are users with a label, False otherwise.
        """
        if UserSpamStatus.objects.filter(Q(label=True) | Q(label=False)).exists():
            return True
        return False

    def load_labels_from_csv(self, filepath=DATASET_FILE_PATH) -> List[int]:
        """
        Load user labels from a CSV file and update the corresponding records in the database.
        This function logs the process and captures any exceptions related to file handling.

        Params:
            filepath (str): The path to the CSV file containing user IDs and labels.
        Returns:
            List[int]: A list of user IDs whose labels were successfully updated.
        """
        logger.info("Loading labels CSV...")
        try:
            label_df = pd.read_csv(filepath)
        except Exception:
            logger.exception("Could not open/read file: {0}".format(filepath))
            logger.exception(
                "Please locate a dataset with labels at the path of ./curator/spam_dataset.csv"
            )

        user_id_list = []
        for idx, row in label_df.iterrows():
            flag = self.update_labels(row["user_id"], bool(row["label"]))
            if flag == 1:
                user_id_list.append(row["user_id"])
        logger.info("Successfully loaded labels from CSV!")
        logger.info(
            "Number of user ids whose label was loaded: {0}".format(len(user_id_list))
        )
        # return user_id_list

    def update_labels(self, user_id: int, label: bool):  # TODO update with batch
        """
        Update the label for a specified user in the database.

        Params:
            user_id (int): The user ID whose label is to be updated.
            label (bool): The label value to set.
        Returns:
            int: 1 if the update was successful, 0 otherwise.
        """
        return UserSpamStatus.objects.filter(member_profile__user_id=user_id).update(
            label=label
        )  # return 0(fail) or 1(success)

    def update_training_data(self, df: DataFrame, is_training_data=True):
        """
        Mark specified users in the DataFrame as training data or not, based on the provided boolean.

        Params:
            df (DataFrame): DataFrame containing user IDs.
            is_training_data (bool): Whether to mark as training data.
        Returns:
            None
        """
        for idx, row in df.iterrows():
            UserSpamStatus.objects.filter(
                member_profile__user_id=row["user_id"]
            ).update(is_training_data=is_training_data)

    def save_predictions(self, prediction_df: DataFrame, context_id: Enum):
        """
        Save spam predictions for users into the database, using the provided DataFrame and context ID.

        Params:
            prediction_df (DataFrame): A DataFrame containing user IDs, predictions, and confidence levels.
            context_id (Enum): The context ID related to the spam predictions.
        Returns:
            None
        """
        for idx, row in prediction_df.iterrows():
            spam_status = UserSpamStatus.objects.get(
                member_profile__user_id=row["user_id"]
            )
            # print(vars(spam_status))
            UserSpamPrediction.objects.get_or_create(
                spam_status=spam_status,
                context_id=context_id.name,
                prediction=row["predictions"],
                confidence=row["confidences"],
            )

        # Batching and get all applicable UserSpamStatus
        # spam_status_Qset = UserSpamStatus.objects.filter(
        #     member_profile__user_id__in=prediction_df['user_id'].tolist()
        # )
        # prediction_df.set_index('user_id')

        # for spam_status_obj in spam_status_Qset:
        #     print(vars(spam_status_obj)) # {'_state': <django.db.models.base.ModelState object at 0x7fd6fa09ad10>, 'member_profile_id': 14, 'label': False, 'last_updated': datetime.datetime(2024, 4, 10, 2, 11, 17, 771830, tzinfo=datetime.timezone.utc), 'is_training_data': False}
        #     user_id = getattr(spam_status_obj, 'member_profile__user_id')
        #     #TODO ask: member_profile__user_id => AttributeError: 'UserSpamStatus' object has no attribute 'member_profile__user_id'
        #     #       vs member_profile_id       => ValueError: 3283 is not in range
        #     UserSpamPrediction.objects.get_or_create(
        #         spam_status = spam_status_obj,
        #         context_id = context_id.name,
        #         prediction = prediction_df.loc[user_id, 'predictions'],
        #         confidence = prediction_df.loc[user_id, 'confidences']
        #     )
