from core.models import MemberProfile
import pandas as pd
from django.contrib.auth.models import User
from itertools import chain
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings("ignore") #ignore warnings


class UserPipeline:
    def __init__(self):
        
        self.columns = ['is_spam', 
                        'first_name', 
                        'last_name', 
                        'is_active', 
                        'email', 
                        'timezone', 
                        'industry', 
                        'affiliations', 
                        'bio', 
                        'research_interests', 
                        'personal_url', 
                        'professional_url', 
                        'spam_likely', #probability / confidence interval
                        'user_id']
        self.user_df = pd.DataFrame(columns=self.columns)

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
                    'user_id': int(i)
                }
                custom_df = custom_df.append(row, ignore_index=True)

        return custom_df


        
    def all_users_df(self):

        all_users = MemberProfile.objects.all()
        for i, x in enumerate(all_users, start=1):
            if x.user is None:
                continue
            else:

                #populate df here:
                row = {'first_name': x.user.first_name, 
                       'last_name': x.user.last_name, 
                       'is_active': x.is_active, 
                       'email': x.email, 
                       'timezone': x.timezone, 
                       'affiliations': x.affiliations, 
                       'bio': x.bio, 
                       'research_interests': x.research_interests, 
                       'personal_url': x.personal_url, 
                       'professional_url': x.professional_url,
                       'user_id' : int(i)
                       }
                
                self.user_df = self.user_df.append(row, ignore_index=True)
        
        return self.user_df


    #filter by date joined
    def users_joined_yesterday_df(self):
        
        yesterday = datetime.now() - timedelta(days=1)    
        query = ({"user__date_joined__gte": yesterday})
        df = self.custom_query_df(query)
        return df
    
    
    def users_joined_last_week_df(self):
        
        one_week_ago = datetime.now() - timedelta(days=7)    
        query = ({"user__date_joined__gte": one_week_ago})
        df = self.custom_query_df(query)
        return df
    
    def users_joined_last_month_df(self):
       
        one_month_ago = datetime.now() - timedelta(days=31)    
        query = ({"user__date_joined__gte": one_month_ago})
        df = self.custom_query_df(query)
        return df

    def users_joined_last_year_df(self):
        
       
        last_year = datetime.now() - timedelta(days=365)    
        query = ({"user__date_joined__gte": last_year})
        df = self.custom_query_df(query)
        return df
    
    #ufilter by user name
    def users_name_contains_df(self, search_string):

        users_name_df = pd.DataFrame(columns=self.columns)
        member_profiles_first = MemberProfile.objects.filter(user__first_name__contains=search_string)
        member_profiles_last = MemberProfile.objects.filter(user__last_name__contains=search_string)

        combined_member_profiles = list(chain(member_profiles_first, member_profiles_last))

        for i, x in enumerate(combined_member_profiles, start=1):
            if x.user is None:
                continue
            else:

                #populate df here:
                row = {'first_name': x.user.first_name, 
                       'last_name': x.user.last_name, 
                       'is_active': x.is_active, 
                       'email': x.email, 
                       'timezone': x.timezone, 
                       'affiliations': x.affiliations, 
                       'bio': x.bio, 
                       'research_interests': x.research_interests, 
                       'personal_url': x.personal_url, 
                       'professional_url': x.professional_url,
                       'user_id': int(i)
                       }
                
                users_name_df = users_name_df.append(row, ignore_index=True)

        return users_name_df
    
    #filter by first name
    def users_first_name_exact_df(self, search_string):

        query = ({"user__first_name__exact": search_string})
        df = self.custom_query_df(query)
        return df
    
    
    
    #filter by last name
    def users_last_name_exact_df(self, search_string):

        query = ({"user__last_name__exact": search_string})
        df = self.custom_query_df(query)
        return df
    
    #filter by email
    def users_email_contains_df(self, search_string):
        
        query = ({"user__email__contains": search_string})
        df = self.custom_query_df(query)
        return df
        
    
    def users_email__exact_df(self, search_string):
        
        query = ({"user__email__exact": search_string})
        df = self.custom_query_df(query)
        return df
    
    # Filter by institution contains
    def users_institution_contains_df(self, search_string):
        query = {"institution__name__contains": search_string}
        df = self.custom_query_df(query)
        return df

    # Filter by exact institution
    def users_institution_exact_df(self, search_string):
        query = {"institution__name__exact": search_string}
        df = self.custom_query_df(query)
        return df
    
    #filter by bio
    def users_bio_contains_df(self, search_string):

        query = {"bio__contains": search_string}
        df = self.custom_query_df(query)
        return df
    
    def users_bio_exact_df(self, search_string):

        query = {"bio__exact": search_string}
        df = self.custom_query_df(query)
        return df
    
    #filter by personal url
    def users_personal_url_contains_df(self, search_string):

        query = {"personal_url__contains": search_string}
        df = self.custom_query_df(query)
        return df
    
    def users_personal_url_exact_df(self, search_string):

        query = {"personal_url__exact": search_string}
        df = self.custom_query_df(query)
        return df
    
    #filter by professional url
    def users_professional_url_contains_df(self, search_string):

        query = {"professional_url__contains": search_string}
        df = self.custom_query_df(query)
        return df
    
    def users_professional_url_exact_df(self, search_string):

        query = {"personal_url__exact": search_string}
        df = self.custom_query_df(query)
        return df
    
    
    def print_user_df(self):
        print(self.user_df.head())
    
    def number_of_users(self):
        all_users = MemberProfile.objects.all()
        return len(all_users)
    
    def user_df_size(self):
        return len(self.user_df)




        


    
    
            

    
        
    




    

