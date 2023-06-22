import pandas as pd
import numpy as np
import re
from django.contrib.auth.models import User
from django.db.models import Q
from itertools import chain
import warnings
from datetime import datetime, timedelta, date

from core.models import MemberProfile
from curator.models import SpamRecommendation

warnings.filterwarnings("ignore") #ignore warnings

class UserPipeline:
    def __init__(self):
        self.column_names = [
                'member_profile__user_id',
                'member_profile__user__first_name',
                'member_profile__user__last_name',
                'member_profile__user__is_active',
                'member_profile__user__email',
                'member_profile__timezone',
                'member_profile__affiliations',
                'member_profile__bio',
                'member_profile__research_interests',
                'member_profile__personal_url',
                'member_profile__professional_url',
                'labelled_by_curator',
                'labelled_by_bio_classifier',
                'labelled_by_user_classifier',
                'bio_classifier_confidence',
                'user_classifier_confidence']
        
        self.type_int_bool_column_names = [
                'member_profile__user_id',
                'labelled_by_curator',
                'labelled_by_bio_classifier',
                'labelled_by_user_classifier',
                'bio_classifier_confidence',
                'user_classifier_confidence']

    def __rename_columns(self, df):
        if df.empty == True: return df
        df.rename(columns = {
                self.column_names[0]: 'user_id',
                self.column_names[1]: 'first_name',
                self.column_names[2]: 'last_name',
                self.column_names[3]: 'is_active',
                self.column_names[4]: 'email',
                self.column_names[5]: 'timezone',
                self.column_names[6]: 'affiliations',
                self.column_names[7]: 'bio',
                self.column_names[8]: 'research_interests',
                self.column_names[9]: 'personal_url',
                self.column_names[10]: 'professional_url'}, inplace = True)
        return df
    
    def __convert_df_markup_to_string(self, df):
        if df.empty == True: return df
        for col in df.columns:
            if col in self.type_int_bool_column_names: df[col] = df[col].astype('Int64')
            else: df[col] = df[col].apply(lambda text: re.sub(r'<.*?>', ' ', str(text))) # Remove markdown
        return df
    
    def load_labels(self, filepath="dataset.csv"):
        # This function updates "labelled_by_curator" field of the SpamRecommendation table bsed on external dataset file.
        # Dataset should have columns named "user_id" and "is_spam"
        # param : filepath of dataset to be loaded
        # return : None
        if SpamRecommendation.objects.all().exists() == False:
            for profile in MemberProfile.objects.all():
                SpamRecommendation(member_profile=profile).save()

        label_df = pd.read_csv(filepath) #TODO : add json read too?
        for idx, row in label_df.iterrows():
            SpamRecommendation.objects.filter(member_profile__user_id=row['user_id']).update(labelled_by_curator=bool(row['is_spam']))
    
    def update_used_for_train(self, df):
        # param : DataFrame of user_ids (int) that were used to train a model
        # return : None
        for idx, row in df.iterrows():
            SpamRecommendation.objects.filter(member_profile__user_id=row['user_id']).update(used_for_train=True)

    def get_all_users_df(self):
        return self.__rename_columns(self.__convert_df_markup_to_string(
            pd.DataFrame(list(SpamRecommendation.objects.all().exclude(member_profile__user_id=None).values(*self.column_names)))))
    
    def get_unlabelled_by_curator_df(self):
        # return : DataFrame of user data that haven't been labeled by curator
        return self.__rename_columns(self.__convert_df_markup_to_string(
            pd.DataFrame(list(SpamRecommendation.objects.exclude(member_profile__user_id=None).filter(labelled_by_curator=None).values(*self.column_names)))))

    def get_untrained_df(self):
        # return : DataFrame of user data that haven't been used for train previously
        return self.__rename_columns(self.__convert_df_markup_to_string(pd.DataFrame(list(SpamRecommendation.objects.exclude(member_profile__user_id=None, labelled_by_curator=None).filter(used_for_train=False).values(*self.column_names)))))
    
    def save_predictions(self, prediction_df, isTextClassifier=False):
        # params : spam_recommendation_df ... a Dataframe with columns "user_id", "labelled_by_{}", and "{}_classifier_confidence" 
        # return : None
        if isTextClassifier:
            for idx, row in prediction_df.iterrows():
                SpamRecommendation.objects.filter(member_profile__user_id=row.user_id).update(
                    labelled_by_bio_classifier=row.labelled_by_bio_classifier,
                    bio_classifier_confidence=row.bio_classifier_confidence
                )
        else: 
            for idx, row in prediction_df.iterrows():
                SpamRecommendation.objects.filter(member_profile__user_id=row.user_id).update(
                    labelled_by_user_classifier=row.labelled_by_user_classifier,
                    user_classifier_confidence=row.user_classifier_confidence
                )


    



        


    
