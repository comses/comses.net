import pandas as pd
from pandas import DataFrame 
import re
from ast import literal_eval
import logging
from django.db.models import Q
from curator.models import UserSpamStatus, UserSpamPrediction
from django.conf import settings
from enum import Enum
#from .spam import PresetContextID

DATASET_FILE_PATH = settings.SPAM_TRAINING_DATASET_PATH
logger = logging.getLogger(__name__)

class UserSpamStatusProcessor:
    """
    UserSpamStatusProcessor
    converts UserSpamStatus querysets into Pandas dataframes.
    The functions are called by SpamClassifier variants.
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
            'string' : ["first_name",
                        "last_name",
                        "email", 
                        "timezone", 
                        "affiliations", 
                        "bio", 
                        "research_interests", 
                        "personal_url", 
                        "professional_url"],
            'categorical' : ["is_active"],
            'numerical' : ["user_id", "label"]
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
        
        self.df_db_field_mapping = dict((v,k) for k,v in self.db_df_field_mapping.items())

    def __rename_df_fields(self, df:DataFrame)->DataFrame:
        if df.empty:
            return df
        
        df.rename(
            columns=self.db_df_field_mapping,
            inplace=True,
        )
        return df

    def __preprocess_fields(self, df:DataFrame)->DataFrame:
            if df.empty:
                return df
            
            for col in df.columns:
                if col in self.field_type['string']:
                    df[col] = df[col].fillna('')
                    df[col] = df[col].apply(lambda text: re.sub(r"<.*?>", " ", str(text))) # Removing markdown
                    if col == 'affiliations': 
                        df[col] = df[col].apply(self.__restructure_affiliation_field)
                    if col == 'email': 
                        df = df.apply(self.__split_email_field, axis=1)
                        df = df.drop('email', axis=1)

                elif col in self.field_type['numerical']:
                    df[col] = df[col].fillna(-1).astype(int)

                elif col in self.field_type['categorical']:
                    df[col] = df[col].fillna('NaN').astype(str)

            return df
    

    def __split_email_field(self,row):
        row['email_username'], row['email_domain'] = row['email'].split('@')
        return row

    def __restructure_affiliation_field(self, array):
        array = literal_eval(array)
        if len(array) != 0:
            result = ""
            for affili_dict in array:
                name = affili_dict["name"] if ('name' in affili_dict.keys()) else ""
                url = affili_dict["url"] if ('url' in affili_dict.keys()) else ""
                ror_id = affili_dict["ror_id"] if ('ror_id' in affili_dict.keys()) else ""
                affili = name + " (" + "url: " + url +", ror id: " + ror_id +"), "
                result = result + affili
            return result
        else:
            return ""

    def __validate_selected_fields(self, selected_fields:list[str])->list[str]:
        """
        only field names that exist in DB will be filter out.
        """
        validated_fields = []
        for field in selected_fields:
            if field in self.df_fields:
                validated_fields.append(field)
        return validated_fields

    def get_all_users(self, selected_fields:list[str])->DataFrame:
        selected_fields = self.__validate_selected_fields(selected_fields)
        selected_fields.append('user_id')
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

    def get_selected_users(self, user_ids:int, selected_fields:list[str])->DataFrame:
        selected_fields = self.__validate_selected_fields(selected_fields)
        selected_fields.append('user_id')
        selected_db_fields = [self.df_db_field_mapping[v] for v in selected_fields]
        return self.__preprocess_fields(
            self.__rename_df_fields(
                DataFrame(
                    list(
                        UserSpamStatus.objects.exclude(
                            member_profile__user_id=None
                        ).filter(member_profile__user_id__in=user_ids)
                        .values(*selected_db_fields)
                    )
                )
            )
        )

    def get_all_users_with_label(self, selected_fields:list[str])->DataFrame:
        selected_fields = self.__validate_selected_fields(selected_fields)
        selected_fields.extend(['label','user_id'])
        selected_db_fields = [self.df_db_field_mapping[v] for v in selected_fields]
        return self.__preprocess_fields(
            self.__rename_df_fields(
                DataFrame(
                    list(
                        UserSpamStatus.objects.exclude(
                            Q(member_profile__user_id=None)
                            | Q(label=None)
                        )
                        .values(*selected_db_fields)
                    )
                )
            )
        )
    
    def get_selected_users_with_label(self, user_ids:int, selected_fields:list[str])->DataFrame:
        selected_fields = self.__validate_selected_fields(selected_fields)
        selected_fields.extend(['label','user_id'])
        selected_db_fields = [self.df_db_field_mapping[v] for v in selected_fields]
        return self.__preprocess_fields(
            self.__rename_df_fields(
                DataFrame(
                    list(
                        UserSpamStatus.objects.exclude(
                            Q(member_profile__user_id=None)
                            | Q(label=None)
                        ).filter(member_profile__user_id__in=user_ids)
                        .values(*selected_db_fields)
                    )
                )
            )
        )
    
    # TODO: tune confidence threshold later
    def get_predicted_spam_users(self, classifier_type:str, confidence_threshold=0.5)->list[int]:
        """
        This functions will first filter out the users predicted as a spam by the selected classifier.
        """
        spam_users = list(
           UserSpamPrediction.objects.filter(
               Q(classifier_type=classifier_type)
               & Q(prediction=True)
               & Q(confidence__gte=confidence_threshold)
           ).values_list("spam_status__member_profile__user_id", flat=True)
        )
        return spam_users  # returns list of spam user_id

    def labels_exist(self)->bool:
        # if there are users with label != None, return True
        if UserSpamStatus.objects.filter(
            Q(label=True) | Q(label=False)
        ).exists():
            return True
        return False
    

    def load_labels_from_csv(self, filepath=DATASET_FILE_PATH)->list[int]:
        """
        This function updates "label" field of the SpamRecommendation table bsed on external dataset file.
        Dataset should have columns named "user_id" and "label"
        param : filepath of dataset to be loaded
        return : list of user_ids which label was updated
        """
        logger.info("Loading labels CSV...")
        try:
            label_df = pd.read_csv(filepath)
        except Exception:
            logger.exception("Could not open/read file: {0}".format(filepath))
            logger.exception("Please locate a dataset with labels at the path of ./curator/spam_dataset.csv")
        
        user_id_list = []
        for idx, row in label_df.iterrows():
            flag = self.update_labels(row["user_id"], bool(row["label"]))
            if flag == 1:
                user_id_list.append(row["user_id"])
        logger.info("Successfully loaded labels from CSV!")
        logger.info("Number of user ids whose label was loaded: {0}".format(len(user_id_list)))
        # return user_id_list

    def update_labels(self, user_id:int, label:bool): #TODO update with batch
        return UserSpamStatus.objects.filter(member_profile__user_id=user_id).update(
            label=label
        )  # return 0(fail) or 1(success)

    def update_training_data(self, df:DataFrame, training_data=True):
        # param : DataFrame of user_ids (int) that were used to train a model
        # return : None
        for idx, row in df.iterrows():
            UserSpamStatus.objects.filter(
                member_profile__user_id=row["user_id"]
            ).update(is_training_data=training_data)

    def save_predictions(self, prediction_df:DataFrame, context_id:Enum):
        # params : prediction_df ... a Dataframe with columns "user_id", "predictions", and "confidences"
        #          context_id ... PresetContextID Enum
        # return : None
        for idx, row in prediction_df.iterrows():
            spam_status = UserSpamStatus.objects.get(member_profile__user_id=row['user_id'])
            print(vars(spam_status))
            UserSpamPrediction.objects.get_or_create(
                spam_status = spam_status,
                context_id = context_id.name,
                prediction = row['predictions'],
                confidence = row['confidences']
            )

        # batching and get all applicable UserSpamStatus
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