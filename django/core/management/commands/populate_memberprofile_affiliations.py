from django.core.management.base import BaseCommand
from fuzzywuzzy import fuzz
import re
import requests
import time
import json
import logging

from core.models import MemberProfile

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Migrate data from MemberProfile.institution to MemberProfile.affiliations with
    an attempt to add more data from ROR database"""

    def add_arguments(self, parser):
        parser.add_argument(
            "--cached",
            type=str
        )

    def handle(self, *args, **options):
        # if options["cached"]:
        #     with open(options["cached"]) as file:
        #         data = json.load(file)

        for mp in MemberProfile.objects.all().order_by('user_id'):
            if mp.institution:
                new_affil = {}

                if mp.institution.name:
                    new_affil["name"] = mp.institution.name
                    best_match = self.lookup(mp.institution.name)

                    if best_match:
                        if (best_match["score"] >= 1.0 and fuzz.partial_ratio(
                            best_match["organization"]["name"], mp.institution.name) >= 75):
                            # add ror_id if we have a confident enough match
                            new_affil["ror_id"] = best_match["organization"]["id"]
                            # add acronym
                            if best_match["organization"]["acronyms"]:
                                new_affil["acronym"] = best_match["organization"]["acronyms"][0]
                            # add link from the response if the user doesn't have one
                            if not mp.institution.url and best_match["organization"]["links"]:
                                new_affil["url"] = best_match["organization"]["links"][0]

                    if mp.institution.url:
                        # fix up urls by adding a default http scheme
                        new_url = mp.institution.url
                        if not re.match(r"^https?://", mp.institution.url):
                            new_url = "http://" + mp.institution.url
                        new_affil["url"] = new_url
               
                    logger.info("adding %s to member %d", new_affil, mp.id)
                    mp.affiliations = [new_affil]
                    mp.save()

    def lookup(self, name):
        # lookup the name with the affiliations parameter in the ror db
        connected = False
        ror_url = "https://api.ror.org/organizations?affiliation="
        res = None
        while not connected:
            try:
                res = requests.get(ror_url + name, timeout=10)
                connected = True
                e = None
            except Exception as e:
                pass
            if e:
                print("connection error. sleeping and trying again..")
                time.sleep(2)
        items = res.json()["items"]
        return items[0] if items else None
