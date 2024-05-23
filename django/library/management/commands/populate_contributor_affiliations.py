from collections import defaultdict
from django.core.management.base import BaseCommand
from fuzzywuzzy import fuzz
from requests.adapters import HTTPAdapter
from urllib3 import Retry

import logging
import requests

from library.models import ContributorAffiliation, Contributor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Migrate data from ContributorAffiliation Tags to Contributor.json_affiliations; attempts to augment data with a basic ROR API lookup"""

    def add_arguments(self, parser):
        parser.add_argument(
            "-r",
            "--ratio",
            type=int,
            choices=range(1, 100),
            metavar="[1-100]",
            default=80,
            help="""threshold used in fuzzy matching and ROR API score (divided by 100 for a floating point number between 0.0 and 1.0). Defaults to 80""",
        )

    def handle(self, *args, **options):
        session = requests.Session()
        fuzzy_match_threshold = options["ratio"]
        ror_score_threshold = fuzzy_match_threshold / 100.0
        adapter = HTTPAdapter(
            max_retries=Retry(
                total=6,
                backoff_factor=1.5,
                allowed_methods=None,
                status_forcelist=[429, 500, 502, 503, 504],
            ),
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        ordered_contributor_affiliations = (
            ContributorAffiliation.objects.all().order_by("content_object_id")
        )

        logger.info("Looking up affiliations against ROR API")

        # build affiliations_by_contributor_id dictionary
        contributor_affiliations = defaultdict(list)
        for ca in ordered_contributor_affiliations:
            if not (ca.tag and ca.tag.name and ca.content_object_id):
                continue

            contributor_id = ca.content_object_id
            affiliation_name = ca.tag.name
            best_match = self.lookup(session, affiliation_name)
            new_affiliation = self.to_affiliation(
                affiliation_name,
                best_match,
                match_threshold=fuzzy_match_threshold,
                ror_score_threshold=ror_score_threshold,
            )
            # register the new affiliation with this contributor
            contributor_affiliations[contributor_id].append(new_affiliation)

        # Loop through enriched affiliations and save the json_affiliations
        # on each contributor
        for contributor_id, affiliations in contributor_affiliations.items():
            logger.info(
                "updating [contributor_id: %s] affiliations=%s",
                contributor_id,
                affiliations,
            )
            Contributor.objects.filter(pk=contributor_id).update(
                json_affiliations=affiliations
            )

    def lookup(self, session, name):
        ror_api_url = f"https://api.ror.org/organizations?affiliation={name}"
        try:
            response = session.get(ror_api_url, timeout=10)
            items = response.json()["items"]
            logger.debug("[lookup %s] found %s", name, items)
            return items[0] if items else None
        except Exception as e:
            logger.warning(e)
        return None

    def to_affiliation(
        self, name, best_match, match_threshold=85, ror_score_threshold=1.0
    ):
        """
        Returns a new affiliation dictionary with ROR data if a good match
        or a dict of the original data { "name": name } otherwise
        """
        if best_match:
            score = best_match["score"]
            ror_name = best_match["organization"]["name"]
            if (
                score >= ror_score_threshold
                or fuzz.partial_ratio(ror_name, name) >= match_threshold
            ):
                new_affiliation = {
                    "name": ror_name,
                    # ror id is guaranteed if lookup was successful
                    "ror_id": best_match["organization"]["id"],
                }
                # acronyms and links are not guaranteed to exist
                if best_match["organization"]["acronyms"]:
                    new_affiliation["acronym"] = best_match["organization"]["acronyms"][
                        0
                    ]
                if best_match["organization"]["links"]:
                    new_affiliation["url"] = best_match["organization"]["links"][0]
                # FIXME: additional geodata to include from the returned ROR API data?
                # e.g., GRID id, 'country', 'aliases', 'types', etc.
                return new_affiliation
            else:
                logger.warning("No reasonable match found for %s: %s", name, best_match)

        # either no best_match or failed the match_threshold fuzz test
        return {
            "name": name,
        }
