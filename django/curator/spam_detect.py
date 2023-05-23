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
                        'spam_likely']
        self.user_df = pd.DataFrame(columns=self.columns)
        
    def all_users_df(self):

        all_users = MemberProfile.objects.all()
        for x in all_users:
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
                       'professional_url': x.professional_url
                       }
                
                self.user_df = self.user_df.append(row, ignore_index=True)
        
        return self.user_df


    #filter by date joined
    def users_joined_yesterday_df(self):
        users_yesterday_df = pd.DataFrame(columns=self.columns)
        current_date = datetime.now().date()

        yesterday = datetime.now() - timedelta(days=1)
        users_joined_yesterday = MemberProfile.objects.filter(user__date_joined__gte=yesterday)

        for x in users_joined_yesterday:
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
                       'professional_url': x.professional_url
                       }
                
                users_yesterday_df = users_yesterday_df.append(row, ignore_index=True)
            
        return users_yesterday_df

    def users_joined_last_week_df(self):
        users_last_week_df = pd.DataFrame(columns=self.columns)
        current_date = datetime.now().date()

        one_week_ago = datetime.now() - timedelta(days=7)
        users_joined_last_week = MemberProfile.objects.filter(user__date_joined__gte=one_week_ago)

        for x in users_joined_last_week:
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
                       'professional_url': x.professional_url
                       }
                
                users_last_week_df = users_last_week_df.append(row, ignore_index=True)
            
        return users_last_week_df
    
    def users_joined_last_month_df(self):
        users_last_month_df = pd.DataFrame(columns=self.columns)
        current_date = datetime.now().date()

        one_month_ago = datetime.now() - timedelta(days=31)
        users_joined_last_month = MemberProfile.objects.filter(user__date_joined__gte=one_month_ago)

        for x in users_joined_last_month:
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
                       'professional_url': x.professional_url
                       }
                
                users_last_month_df = users_last_month_df.append(row, ignore_index=True)
        
        return users_last_month_df

    def users_joined_last_year_df(self):
        users_last_year_df = pd.DataFrame(columns=self.columns)
        current_date = datetime.now().date()

        one_year_ago = datetime.now() - timedelta(days=365)
        users_joined_last_year = MemberProfile.objects.filter(user__date_joined__gte=one_year_ago)


        for x in users_joined_last_year:
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
                       'professional_url': x.professional_url
                       }
                
                users_last_year_df = users_last_year_df.append(row, ignore_index=True)

        return users_last_year_df
    
    #ufilter by user name
    def users_name_contains_df(self, search_string):

        users_name_df = pd.DataFrame(columns=self.columns)
        member_profiles_first = MemberProfile.objects.filter(user__first_name__contains=search_string)
        member_profiles_last = MemberProfile.objects.filter(user__last_name__contains=search_string)

        combined_member_profiles = list(chain(member_profiles_first, member_profiles_last))

        for x in combined_member_profiles:
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
                       'professional_url': x.professional_url
                       }
                
                users_name_df = users_name_df.append(row, ignore_index=True)

        return users_name_df
    
    #filter by first name
    def users_first_name_exact_df(self, search_string):

        users_first_df = pd.DataFrame(columns=self.columns)

        member_profiles = MemberProfile.objects.filter(user__first_name__exact=search_string)


        for x in member_profiles:
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
                       'professional_url': x.professional_url
                       }
                
                users_first_df = users_first_df.append(row, ignore_index=True)

        return users_first_df
    
    #filter by last name
    def users_last_name_exact_df(self, search_string):

        users_last_df = pd.DataFrame(columns=self.columns)

        member_profiles = MemberProfile.objects.filter(user__last_name__exact=search_string)


        for x in member_profiles:
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
                       'professional_url': x.professional_url
                       }
                
                users_last_df = users_last_df.append(row, ignore_index=True)

        return users_last_df
    
    #filter by email
    def users_email_contains_df(self, search_string):
        
        users_email_df = pd.DataFrame(columns=self.columns)

        member_profiles = MemberProfile.objects.filter(user__email__contains=search_string)

        for x in member_profiles:
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
                       'professional_url': x.professional_url
                       }
                
                users_email_df = users_email_df.append(row, ignore_index=True)

        return users_email_df
    
    def users_email__exact_df(self, search_string):
        
        users_email_df = pd.DataFrame(columns=self.columns)

        member_profiles = MemberProfile.objects.filter(user__email__exact=search_string)

        for x in member_profiles:
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
                       'professional_url': x.professional_url
                       }
                
                users_email_df = users_email_df.append(row, ignore_index=True)

        return users_email_df
    
    #filter by institution
    def users_institution_contains_df(self, search_string):

        users_institution_df = pd.DataFrame(columns=self.columns)

        member_profiles = MemberProfile.objects.filter(institution__name__contains=search_string)

        for x in member_profiles:
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
                       'professional_url': x.professional_url
                       }
                
                users_institution_df = users_institution_df.append(row, ignore_index=True)

        return users_institution_df
    
    def users_institution__exact_df(self, search_string):

        users_institution_df = pd.DataFrame(columns=self.columns)

        member_profiles = MemberProfile.objects.filter(institution__name__exact=search_string)

        for x in member_profiles:
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
                       'professional_url': x.professional_url
                       }
                
                users_institution_df = users_institution_df.append(row, ignore_index=True)

        return users_institution_df
    
    #filter by bio
    def users_bio_contains_df(self, search_string):

        users_bio_df = pd.DataFrame(columns=self.columns)

        member_profiles = MemberProfile.objects.filter(bio__contains=search_string)

        for x in member_profiles:
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
                       'professional_url': x.professional_url
                       }
                
                users_bio_df = users_bio_df.append(row, ignore_index=True)

        return users_bio_df
    
    def users_bio_exact_df(self, search_string):

        users_bio_df = pd.DataFrame(columns=self.columns)

        member_profiles = MemberProfile.objects.filter(bio__exact=search_string)

        for x in member_profiles:
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
                       'professional_url': x.professional_url
                       }
                
                users_bio_df = users_bio_df.append(row, ignore_index=True)

        return users_bio_df
    
    #filter by personal url
    def users_personal_url_contains_df(self, search_string):

        users_personal_url_df = pd.DataFrame(columns=self.columns)
        member_profiles = MemberProfile.objects.filter(personal_url__contains=search_string)

        for x in member_profiles:
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
                       'professional_url': x.professional_url
                       }
                
                users_personal_url_df = users_personal_url_df.append(row, ignore_index=True)

        return users_personal_url_df
    
    def users_personal_url_exact_df(self, search_string):

        users_personal_url_df = pd.DataFrame(columns=self.columns)
        member_profiles = MemberProfile.objects.filter(personal_url__exact=search_string)

        for x in member_profiles:
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
                       'professional_url': x.professional_url
                       }
                
                users_personal_url_df = users_personal_url_df.append(row, ignore_index=True)

        return users_personal_url_df
    
    #filter by professional url
    def users_professional_url_contains_df(self, search_string):

        users_professional_url_df = pd.DataFrame(columns=self.columns)
        member_profiles = MemberProfile.objects.filter(professional_url__contains=search_string)

        for x in member_profiles:
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
                       'professional_url': x.professional_url
                       }
                
                users_professional_url_df = users_professional_url_df.append(row, ignore_index=True)

        return users_professional_url_df
    
    def users_professional_url_exact_df(self, search_string):

        users_professional_url_df = pd.DataFrame(columns=self.columns)
        member_profiles = MemberProfile.objects.filter(professional_url__exact=search_string)

        for x in member_profiles:
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
                       'professional_url': x.professional_url
                       }
                
                users_professional_url_df = users_professional_url_df.append(row, ignore_index=True)

        return users_professional_url_df
    
    
    def print_user_df(self):
        print(self.user_df.head())
    
    def number_of_users(self):
        all_users = MemberProfile.objects.all()
        return len(all_users)
    
    def user_df_size(self):
        return len(self.user_df)




        


    
    
            

    
        
    




    

