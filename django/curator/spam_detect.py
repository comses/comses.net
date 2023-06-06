from core.models import MemberProfile
import pandas as pd
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
        
    def retrieve_spam_data(row):
        row['is_spam'] = False
        row['is_likely'] = False
        if str(row['user__id']) != 'nan': 
            spam_recommendation = SpamRecommendation.objects.filter(Q(member_profile__id=row['user__id']))
            if len(spam_recommendation) > 0:
                print('BONKUS')
                row['is_spam'] = spam_recommendation[0].is_spam_labelled_by_curator
                row['is_likely'] = spam_recommendation[0].is_spam_labelled_by_classifier
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

    def load_is_spam(self):

        pass

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
        df['is_spam'] = None
        df['spam_likely'] = None
        return df
    
    
    def users_joined_last_week_df(self):
        
        one_week_ago = datetime.now() - timedelta(days=7)    
        query = ({"user__date_joined__gte": one_week_ago})
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df['is_spam'] = None
        df['spam_likely'] = None
        return df
    
    def users_joined_last_month_df(self):
       
        one_month_ago = datetime.now() - timedelta(days=31)    
        query = ({"user__date_joined__gte": one_month_ago})
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df['is_spam'] = None
        df['spam_likely'] = None
        return df

    def users_joined_last_year_df(self):
        
       
        last_year = datetime.now() - timedelta(days=365)    
        query = ({"user__date_joined__gte": last_year})
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df['is_spam'] = None
        df['spam_likely'] = None
        return df
    
    #filter by first and last name
    def users_name_contains_df(self, search_string):

        member_profiles_first = MemberProfile.objects.filter(user__first_name__contains=search_string)
        member_profiles_last = MemberProfile.objects.filter(user__last_name__contains=search_string)

        combined_member_profiles = chain(member_profiles_first, member_profiles_last)

        data = MemberProfile.objects.filter(pk__in=[profile.pk for profile in combined_member_profiles]).values(*self.column_names)
        df = pd.DataFrame(data)
        df['is_spam'] = None
        df['spam_likely'] = None

        return df
    
    #filter by first name
    def users_first_name_exact_df(self, search_string):

        query = ({"user__first_name__exact": search_string})
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df['is_spam'] = None
        df['spam_likely'] = None
        return df
    
    
    #filter by last name
    def users_last_name_exact_df(self, search_string):

        query = ({"user__last_name__exact": search_string})
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df['is_spam'] = None
        df['spam_likely'] = None
        return df
    
    #filter by email
    def users_email_contains_df(self, search_string):
        
        query = ({"user__email__contains": search_string})
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df['is_spam'] = None
        df['spam_likely'] = None
        return df
        
    
    def users_email__exact_df(self, search_string):
        
        query = ({"user__email__exact": search_string})
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df['is_spam'] = None
        df['spam_likely'] = None
        return df
    
    # Filter by institution contains
    def users_institution_contains_df(self, search_string):
        query = {"institution__name__contains": search_string}
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df['is_spam'] = None
        df['spam_likely'] = None
        return df

    # Filter by exact institution
    def users_institution_exact_df(self, search_string):
        query = {"institution__name__exact": search_string}
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df['is_spam'] = None
        df['spam_likely'] = None
        return df
    
    #filter by bio
    def users_bio_contains_df(self, search_string):

        query = {"bio__contains": search_string}
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df['is_spam'] = None
        df['spam_likely'] = None
        return df
    
    def users_bio_exact_df(self, search_string):

        query = {"bio__exact": search_string}
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df['is_spam'] = None
        df['spam_likely'] = None
        return df
    
    #filter by personal url
    def users_personal_url_contains_df(self, search_string):

        query = {"personal_url__contains": search_string}
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df['is_spam'] = None
        df['spam_likely'] = None
        return df
    
    def users_personal_url_exact_df(self, search_string):

        query = {"personal_url__exact": search_string}
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df['is_spam'] = None
        df['spam_likely'] = None
        return df
    
    #filter by professional url
    def users_professional_url_contains_df(self, search_string):

        query = {"professional_url__contains": search_string}
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df['is_spam'] = None
        df['spam_likely'] = None
        return df
    
    def users_professional_url_exact_df(self, search_string):

        query = {"personal_url__exact": search_string}
        df = pd.DataFrame(list(MemberProfile.objects.filter(**query).values(*self.column_names)))
        df['is_spam'] = None
        df['spam_likely'] = None
        return df
    
    
    def print_user_df(self):
        print(self.user_df.head())
    
    def number_of_users(self):
        all_users = MemberProfile.objects.all()
        return len(all_users)
    
    def user_df_size(self):
        return len(self.user_df)




        


    
    
            

    
        
    




    

