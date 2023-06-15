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
                'labelled_by_user_classifier']
        
        self.type_int_bool_column_names = [
                'member_profile__user_id',
                'labelled_by_curator',
                # 'member_profile__user__is_active',
                # 'labelled_by_bio_classifier',
                # 'labelled_by_user_classifier'
                ]

    def __rename_columns(self, df):
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
    
    def __convert_df_markup_to_string(self, df): # TODO: conbine with Noel's conversion function
        for col in df.columns:
            if col in self.type_int_bool_column_names:
                df[col] = df[col].values.astype('int')
            else:
                df[col] = df[col].apply(lambda text: re.sub(r'<.*?>', ' ', str(text))) # Remove markdown
        return df
    
    def load_labels(self, filepath="dataset.csv"):
        # This function updates "labelled_by_curator" field of the SpamRecommendation table bsed on external dataset file.
        # Dataset should have columns named "user_id" and "is_spam"
        # param : filepath of dataset to be loaded
        if SpamRecommendation.objects.all().exists() == False:
            for profile in MemberProfile.objects.all():
                SpamRecommendation(member_profile=profile).save()

        label_df = pd.read_csv(filepath)
        for idx, row in label_df.iterrows():
            SpamRecommendation.objects.filter(member_profile__user_id=row['user_id']).update(labelled_by_curator=bool(row['is_spam']))
    
    def save_recommendations(self, spam_recommendation_df):
        # TODO Noel: Update it to include Aiko's classifier fields as well.
        spam_recommendation_df = spam_recommendation_df[[
            'user_id', 
            'labelled_by_bio_classifier', 
            'bio_classifier_confidence'
        ]]
        spam_recommendation_df = spam_recommendation_df.replace(np.nan, None)

        for index, spam_recommendation in spam_recommendation_df.iterrows():
            member_profile = MemberProfile.objects.filter(user__id=spam_recommendation.user__id)[0]
            spam_recommendation = SpamRecommendation(
                member_profile=member_profile,
                labelled_by_bio_classifier=spam_recommendation.labelled_by_bio_classifier,
                bio_classifier_confidence=spam_recommendation.bio_classifier_confidence
            )
            spam_recommendation.save()
        return spam_recommendation_df
    
    def update_used_for_train(self, df):
        # param : DataFrame of user_ids (int) that were used to train a model
        for idx, row in df.iterrows():
            SpamRecommendation.objects.filter(member_profile__user_id=row['user_id']).update(used_for_train=True)

    def get_all_users_df(self):
        user_list = list(SpamRecommendation.objects.all().exclude(member_profile__user_id=None).values(*self.column_names))
        if len(user_list) == 0:
            return None
        return self.__rename_columns(self.__convert_df_markup_to_string(pd.DataFrame(user_list)))
    
    def get_unlabelled_by_curator_df(self):
        # return : DataFrame of user data that haven't been labeled by curator
        user_list = list(SpamRecommendation.objects.exclude(member_profile__user_id=None).filter(labelled_by_curator=None).values(*self.column_names))
        if len(user_list) == 0:
            return None
        return self.__rename_columns(self.__convert_df_markup_to_string(pd.DataFrame(user_list)))

    def get_untrained_df(self):
        # return : DataFrame of user data that haven't been used for train previously
        user_list = list(SpamRecommendation.objects.exclude(labelled_by_curator=None).values(*self.column_names))
        return self.__rename_columns(self.__convert_df_markup_to_string(pd.DataFrame(user_list)))
    
