from core.models import MemberProfile
import pandas as pd
import numpy as np
from django.contrib.auth.models import User
from django.db.models import Q
from itertools import chain
import warnings
from datetime import datetime, timedelta
from curator.models import SpamRecommendation

warnings.filterwarnings("ignore") #ignore warnings


class UserPipeline:
    def __init__(self):
        
        self.column_names = ['user__first_name',
                'user__last_name',
                'user__is_active',
                'user__email',
                'timezone',
                'affiliations',
                'bio',
                'research_interests',
                'personal_url',
                'professional_url',
                'user__id']
    
    def initalize_SpamRecommendation(self):
        # Initalize the SpamRecommendation table
        member_profiles = MemberProfile.objects.all()
        for profile in member_profiles:
            SpamRecommendation(member_profile=profile).save()

    def load_labels(self, filepath): #TODO Aiko: check whether SpamRecommendation has correct field
        if SpamRecommendation.objects.all().exists() == False:
            self.initalize_SpamRecommendation()

        # Update "labelled_by_curator" field of the SpamRecommendation table
        label_df = pd.read_csv(filepath)
        for idx, row in label_df.iterrows():
            SpamRecommendation.objects.filter(Q(member_profile__id=row['user_id']))[0].update(labelled_by_curator=bool(row['is_spam']))

    def retrieve_spam_data(row):
        row['labelled_by_curator'] = False
        row['labelled_by_bio_classifier'] = False
        if str(row['user__id']) != 'nan': 
            spam_recommendation = SpamRecommendation.objects.filter(Q(member_profile__id=row['user__id']))
            if len(spam_recommendation) > 0:
                row['labelled_by_curator'] = spam_recommendation[0].labelled_by_curator
                row['labelled_by_bio_classifier'] = spam_recommendation[0].labelled_by_bio_classifier
        return row

    def custom_query_df(self, query_set):
        member_profiles = MemberProfile.objects.filter(**query_set)
        custom_df = pd.DataFrame(columns=['first_name', 'last_name', 'is_active', 'email', 'timezone',
                                        'affiliations', 'bio', 'research_interests', 'personal_url',
                                        'professional_url'])

        for i, profile in enumerate(member_profiles, start=1):
            if profile.user is not None:
                row = {
                    'first_name': profile.user.first_name,
                    'last_name': profile.user.last_name,
                    'is_active': profile.is_active,
                    'email': profile.email,
                    'timezone': profile.timezone,
                    'affiliations': profile.affiliations,
                    'bio': profile.bio,
                    'research_interests': profile.research_interests,
                    'personal_url': profile.personal_url,
                    'professional_url': profile.professional_url,
                    'user_id': int(i) #use profile.user_id instead
                }
                custom_df = custom_df.append(row, ignore_index=True)

        return custom_df

    #load all users into a dataframe
    def all_users_df(self):

        df = pd.DataFrame(list(MemberProfile.objects.all().values(*self.column_names)))
        df = df.apply(lambda row : UserPipeline.retrieve_spam_data(row), axis=1)

        for col in self.column_names:
            if col == "user__id":
                df[col] = df[col].values.astype('int')
            df[col] = df[col].apply(lambda x: str(x).replace('\r\n','<br />').replace('\n','<br />'))

        df.rename(columns = {'user__first_name': 'first_name',
                             'user__last_name': 'last_name',
                             'user__is_active': 'is_active',
                             'user__email': 'email',
                             'user__id': 'user_id'}, inplace = True)
        return df

    #filter by date joined
    def users_joined_yesterday_df(self):
        
        yesterday = datetime.now() - timedelta(days=1)    
        query = {"user__date_joined__gte": yesterday}
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df = df.apply(lambda row : UserPipeline.retrieve_spam_data(row), axis=1)

        return df
    
    def save_recommendations(self, spam_recommendation_df):
        spam_recommendation_df = spam_recommendation_df[[
            'user__id', 
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
    
    def filtered_by_labelled_df(self, is_labelled : bool):
        if is_labelled == None: labelled_member_profiles = SpamRecommendation.objects.filter(labelled_by_curator=is_labelled)
        else:labelled_member_profiles = SpamRecommendation.objects.exclude(labelled_by_curator=None)

        labelled_member_profiles = set([recommendation.member_profile.user.id for recommendation in labelled_member_profiles])
        unlabelled_member_profiles = MemberProfile.objects.all().values(*self.column_names)
        unlabelled_member_profiles = pd.DataFrame(unlabelled_member_profiles)
        filter_unlabelled = unlabelled_member_profiles.apply(lambda row : row['user__id'] not in labelled_member_profiles, axis=1)
        unlabelled_member_profiles = unlabelled_member_profiles[filter_unlabelled]
        return unlabelled_member_profiles
    
    def users_joined_last_week_df(self):
        
        one_week_ago = datetime.now() - timedelta(days=7)    
        query = ({"user__date_joined__gte": one_week_ago})
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df = df.apply(lambda row : UserPipeline.retrieve_spam_data(row), axis=1)

        return df
    
    def users_joined_last_month_df(self):
       
        one_month_ago = datetime.now() - timedelta(days=31)    
        query = ({"user__date_joined__gte": one_month_ago})
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df = df.apply(lambda row : UserPipeline.retrieve_spam_data(row), axis=1)

        return df

    def users_joined_last_year_df(self):
        
       
        last_year = datetime.now() - timedelta(days=365)    
        query = ({"user__date_joined__gte": last_year})
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df = df.apply(lambda row : UserPipeline.retrieve_spam_data(row), axis=1)

        return df
    
    #filter by first and last name
    def users_name_contains_df(self, search_string):

        member_profiles_first = MemberProfile.objects.filter(user__first_name__contains=search_string)
        member_profiles_last = MemberProfile.objects.filter(user__last_name__contains=search_string)

        combined_member_profiles = chain(member_profiles_first, member_profiles_last)

        data = MemberProfile.objects.filter(pk__in=[profile.pk for profile in combined_member_profiles]).values(*self.column_names)
        df = pd.DataFrame(data)
        df = df.apply(lambda row : UserPipeline.retrieve_spam_data(row), axis=1)

        return df
    
    #filter by first name
    def users_first_name_exact_df(self, search_string):

        query = ({"user__first_name__exact": search_string})
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df = df.apply(lambda row : UserPipeline.retrieve_spam_data(row), axis=1)

        return df
    
    
    #filter by last name
    def users_last_name_exact_df(self, search_string):

        query = ({"user__last_name__exact": search_string})
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df = df.apply(lambda row : UserPipeline.retrieve_spam_data(row), axis=1)

        return df
    
    #filter by email
    def users_email_contains_df(self, search_string):
        
        query = ({"user__email__contains": search_string})
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df = df.apply(lambda row : UserPipeline.retrieve_spam_data(row), axis=1)
        return df
        
    
    def users_email__exact_df(self, search_string):
        
        query = ({"user__email__exact": search_string})
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        
        df = df.apply(lambda row : UserPipeline.retrieve_spam_data(row), axis=1)
        return df
    
    # Filter by institution contains
    def users_institution_contains_df(self, search_string):
        query = {"institution__name__contains": search_string}
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        
        df = df.apply(lambda row : UserPipeline.retrieve_spam_data(row), axis=1)
        return df

    # Filter by exact institution
    def users_institution_exact_df(self, search_string):
        query = {"institution__name__exact": search_string}
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        
        df = df.apply(lambda row : UserPipeline.retrieve_spam_data(row), axis=1)
        return df
    
    #filter by bio
    def users_bio_contains_df(self, search_string):

        query = {"bio__contains": search_string}
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        
        df = df.apply(lambda row : UserPipeline.retrieve_spam_data(row), axis=1)
        return df
    
    def users_bio_exact_df(self, search_string):

        query = {"bio__exact": search_string}
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        
        df = df.apply(lambda row : UserPipeline.retrieve_spam_data(row), axis=1)
        return df
    
    #filter by personal url
    def users_personal_url_contains_df(self, search_string):

        query = {"personal_url__contains": search_string}
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        
        df = df.apply(lambda row : UserPipeline.retrieve_spam_data(row), axis=1)
        return df
    
    def users_personal_url_exact_df(self, search_string):

        query = {"personal_url__exact": search_string}
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        
        df = df.apply(lambda row : UserPipeline.retrieve_spam_data(row), axis=1)
        return df
    
    #filter by professional url
    def users_professional_url_contains_df(self, search_string):

        query = {"professional_url__contains": search_string}
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        
        df = df.apply(lambda row : UserPipeline.retrieve_spam_data(row), axis=1)
        return df
    
    def users_professional_url_exact_df(self, search_string):

        query = {"personal_url__exact": search_string}
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        
        df = df.apply(lambda row : UserPipeline.retrieve_spam_data(row), axis=1)
        return df
    
    
    def print_user_df(self):
        print(self.user_df.head())
    
    def number_of_users(self):
        all_users = MemberProfile.objects.all()
        return len(all_users)
    
    def user_df_size(self):
        return len(self.user_df)




        


    
    
            

    
        
    




    

