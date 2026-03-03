import argparse
import json
import logging
import requests

from django.conf import settings
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

    def _build_ror_api_url(self, query):
        return f"{settings.ROR_API_URL}/{query}"

    def lookup_ror_id(self, ror_id, session):
        # FIXME: should consider creating a simple ROR module to handle interactions with the ROR API
        # and extraction of metadata from their schema though currently only used here,
        # populate_memberprofile_affiliations, and in the frontend ror.ts api
        # may also benefit from the pydantic schema work that @sgfost is doing with codemeticulous
        api_url = self._build_ror_api_url(ror_id)
        try:
            response = session.get(api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.debug("ROR response: %s", data)
            print("\nJSON: ", json.dumps(data, indent=4), "\n")
            print(".", end="", flush=True)
            location = data["locations"][0]
            ror_data = {
                "name": "",
                "aliases": [],
                "acronyms": [],
                "link": "",
                "types": data["types"],
                "wikipedia_url": "",
                "wikidata": "",
                "location": location,
            }
            geonames_details = location["geonames_details"]
            if geonames_details:
                ror_data.update(
                    coordinates={
                        "lat": geonames_details["lat"],
                        "lon": geonames_details["lng"],
                    },
                )
            for name_object in data["names"]:
                if "ror_display" in name_object["types"]:
                    ror_data["name"] = name_object["value"]
                if "alias" in name_object["types"]:
                    ror_data["aliases"].append(name_object)
                if "acronym" in name_object["types"]:
                    ror_data["acronyms"].append(name_object)
            for link_object in data["links"]:
                if link_object["type"] == "website":
                    ror_data["link"] = link_object["value"]
                if link_object["type"] == "wikipedia":
                    ror_data["wikipedia_url"] = link_object["value"]
            for external_id_object in data["external_ids"]:
                if external_id_object["type"] == "wikidata":
                    ror_data["wikidata"] = external_id_object["all"][0]

            return ror_data

        except requests.RequestException:
            print("E", end="", flush=True)
            logger.warning("Unable to retrieve ROR data for %s", ror_id)
            return {}
