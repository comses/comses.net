from django.core.management.base import BaseCommand
from core.models import MemberProfile
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Remove coordinates from each affiliation in all member profiles"""

    def handle(self, *args, **options):
        all_member_profiles = MemberProfile.objects.all()

        for profile in all_member_profiles:
            updated = False
            affiliations = profile.affiliations 

            
            for affiliation in affiliations:
                
                if "coordinates" in affiliation:
                    del affiliation["coordinates"]
                    #del affiliation["links"]
                    #del affiliation["types"]
                    updated = True
            
            if updated:
                profile.affiliations = affiliations
                profile.save()
                

       
