from django.core.management.base import BaseCommand
from core.models import MemberProfile
import requests
import time
import logging
from pathlib import Path
import concurrent.futures
import json
import http.server
import socketserver
import argparse


from core.models import MemberProfile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """something"""

    def __init__(self):
        super().__init__()
        self.session = requests.Session()

    def lookup_ror_id(self, ror_id):
        api_url = f"https://api.ror.org/organizations/{ror_id}"
        try:
            response = self.session.get(api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            print(".", end="", flush=True)
            return data["name"], data["addresses"][0]["lat"], data["addresses"][0]["lng"], data["links"][0], data["types"][0]
        except requests.RequestException as e:
            print("E", end="", flush=True)
            return None, None, None, None, None
    


    def handle(self, *args, **options):
        # TODO: look up every memberprofile.affiliations that has a ror_id and add the lat, lon to each json record
        #add sessions to make faster
        #get links and types as well
        #make metrics.py function to get list of institution data
        all_member_profiles = MemberProfile.objects.all()

        for profile in all_member_profiles:

            updated = False
            affiliations = profile.affiliations


            for affiliation in affiliations:
                if "ror_id" not in affiliation:
                    continue
            
                if "coordinates" not in affiliation:
                    name, lat, lon, links, types = self.lookup_ror_id(affiliation["ror_id"])
                    if lat is not None and lon is not None:
                        affiliation["name"] = name
                        affiliation["coordinates"] = {"lat": lat, "lon": lon}
                        affiliation["link"] = links
                        affiliation["type"] = types
                        updated = True

            if updated:
                profile.affiliations = affiliations
                profile.save()
        
        self.session.close() 

    
