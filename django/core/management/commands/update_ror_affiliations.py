import argparse
import logging
import requests

from django.core.management.base import BaseCommand

from core.models import MemberProfile


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Update all MemberProfile affiliations with lat/lon locations pulled from the ROR API"""

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
            return {
                "name": data["name"],
                "coordinates": {
                    "lat": data["addresses"][0]["lat"],
                    "lon": data["addresses"][0]["lng"],
                },
                "link": data["links"][0],
                "type": data["types"][0],
            }
        except requests.RequestException:
            print("E", end="", flush=True)
            return {}

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action=argparse.BooleanOptionalAction,
            default=False,
            dest="force",
            help="Force update of all affiliations with geo lat/lon data, name, link, and type",
        )

    def handle(self, *args, **options):
        # TODO: look up every memberprofile.affiliations that has a ror_id and add the lat, lon to each json record
        # add sessions to make faster
        # get links and types as well
        # make metrics.py function to get list of institution data
        force = options["force"]
        all_member_profiles = MemberProfile.objects.all()

        for profile in all_member_profiles:

            updated = False
            for affiliation in profile.affiliations:
                if "ror_id" not in affiliation:
                    continue
                if "coordinates" not in affiliation or force:
                    updated_affiliation_data = self.lookup_ror_id(affiliation["ror_id"])
                    if updated_affiliation_data:
                        affiliation.update(**updated_affiliation_data)
                        updated = True

            if updated:
                profile.save()

        self.session.close()
