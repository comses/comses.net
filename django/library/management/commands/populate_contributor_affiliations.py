from collections import defaultdict
from django.core.management.base import BaseCommand
from fuzzywuzzy import fuzz

import logging
import requests
import time

from library.models import ContributorAffiliation, Contributor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Migrate data from ContributorAffiliation Tags to Contributor.json_affiliations
    with an attempt to add more data from ROR database"""

    def add_arguments(self, parser):
        parser.add_argument(
            "-r",
            "--ratio",
            type=int,
            choices=range(1, 100),
            metavar="[1-100]",
            default=75,
            help="ratio threshold used in fuzzy matching, defaults to 75",
        )

    def handle(self, *args, **options):
        session = requests.Session()

        ordered_contributor_affiliations = (
            ContributorAffiliation.objects.all().order_by("content_object_id")
        )

        logger.info("Looking up affiliations against ROR API")

        # build affiliations_by_contributor_id dictionary
        contributor_affiliations_dict = defaultdict(list)
        for ca in ordered_contributor_affiliations:
            if not (ca.tag and ca.tag.name and ca.content_object_id):
                continue

            contributor_id = ca.content_object_id

            new_affiliation = {}
            new_affiliation["name"] = ca.tag.name
            best_match = self.lookup(session, ca.tag.name)

            if best_match and self.is_good_match(
                score=best_match["score"],
                name=ca.tag.name,
                match_name=best_match["organization"]["name"],
                ratio=options["ratio"],
            ):
                # ror_id is guaranteed to exist in the lookup
                new_affiliation["ror_id"] = best_match["organization"]["id"]
                # acronyms and links are not guaranteed to exist
                if best_match["organization"]["acronyms"]:
                    new_affiliation["acronym"] = best_match["organization"]["acronyms"][
                        0
                    ]
                if best_match["organization"]["links"]:
                    new_affiliation["url"] = best_match["organization"]["links"][0]

            # Check if the ID already exists in the affiliations_by_contributor_id dictionary
            contributor_affiliations_dict[contributor_id].append(new_affiliation)

        # Loop through enriched affiliations and save the json_affiliations on contributor
        for contributor_id, affiliations in contributor_affiliations_dict.items():
            # Check if the affiliations list is not empty
            if affiliations:
                logger.info(
                    "Saving affiliations=%s for contributor_id=%s",
                    affiliations,
                    contributor_id,
                )
                contributor = Contributor.objects.get(pk=contributor_id)
                contributor.json_affiliations = affiliations
                contributor.save()

    def lookup(self, session, name):
        # FIXME: replace with exponential backoff (con: adds another dependency)
        # or https://majornetwork.net/2022/04/handling-retries-in-python-requests/
        # lookup the name with the affiliations parameter in the ror db
        connected = False
        ror_api_url = f"https://api.ror.org/organizations?affiliation={name}"
        res = None
        while not connected:
            try:
                res = session.get(ror_api_url, timeout=10)
                connected = True
                e = None
            except Exception as e:
                pass
            if e:
                logger.warning("connection error. sleeping and trying again..")
                time.sleep(2)
        items = res.json()["items"]
        return items[0] if items else None

    def is_good_match(self, score, name, match_name, ratio):
        # returns True if we have high confidence in name matching
        return score >= 1.0 and fuzz.partial_ratio(match_name, name) >= ratio
