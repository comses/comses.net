import argparse
import logging
import requests

from django.core.management.base import BaseCommand

from core.models import MemberProfile


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Update all MemberProfile affiliations with lat/lon locations pulled from the ROR API"""

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action=argparse.BooleanOptionalAction,
            default=False,
            dest="force",
            help="Force update of all affiliations with geo lat/lon data, name, link, and type",
        )

    def handle(self, *args, **options):
        """
        Inspects and updates all active MemberProfiles with affiliations with lat/lon coordinate data from the ROR API
        """
        force = options["force"]
        with requests.Session() as session:

            for profile in MemberProfile.objects.public().with_affiliations():

                should_update_profile = False
                for affiliation in profile.affiliations:
                    if "ror_id" not in affiliation:
                        continue
                    if "coordinates" not in affiliation or force:
                        updated_affiliation_data = self.lookup_ror_id(
                            affiliation["ror_id"], session
                        )
                        if updated_affiliation_data:
                            affiliation.update(**updated_affiliation_data)
                            should_update_profile = True

                if should_update_profile:
                    profile.save()

    def lookup_ror_id(self, ror_id, session):
        # FIXME: should consider creating a simple ROR module to handle interactions with the ROR API
        # though currently only used here and populate_memberprofile_affiliations
        api_url = f"https://api.ror.org/organizations/{ror_id}"
        try:
            response = session.get(api_url, timeout=10)
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
            logger.warning("Unable to retrieve ROR data for %s", ror_id)
            return {}
