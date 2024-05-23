from django.core.management.base import BaseCommand
from rapidfuzz import fuzz
import re
import requests
import time
import logging

from core.models import MemberProfile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Migrate data from MemberProfile.institution to MemberProfile.affiliations
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

        for mp in MemberProfile.objects.all().order_by("user_id"):
            if not (mp.institution and mp.institution.name):
                continue

            new_affil = {}
            new_affil["name"] = mp.institution.name
            best_match = self.lookup(session, mp.institution.name)

            if best_match and self.is_good_match(
                score=best_match["score"],
                name=mp.institution.name,
                match_name=best_match["organization"]["name"],
                ratio=options["ratio"],
            ):
                # ror_id is guaranteed to exist in the lookup
                new_affil["ror_id"] = best_match["organization"]["id"]
                # acronyms and links are not guaranteed to exist
                if best_match["organization"]["acronyms"]:
                    new_affil["acronym"] = best_match["organization"]["acronyms"][0]
                if best_match["organization"]["links"]:
                    new_affil["url"] = best_match["organization"]["links"][0]

            elif mp.institution.url:
                # fix up urls if there wasn't a match and one exists on the profile
                new_affil["url"] = self.fix_url(mp.institution.url)

            logger.info("adding %s to member %d", new_affil, mp.user_id)
            mp.affiliations = [new_affil]
            mp.save()

    def lookup(self, session, name):
        # lookup the name with the affiliations parameter in the ror db
        connected = False
        ror_url = "https://api.ror.org/organizations?affiliation="
        res = None
        while not connected:
            try:
                res = session.get(ror_url + name, timeout=10)
                connected = True
                e = None
            except Exception as e:
                pass
            if e:
                print("connection error. sleeping and trying again..")
                time.sleep(2)
        items = res.json()["items"]
        return items[0] if items else None

    def is_good_match(self, score, name, match_name, ratio):
        # returns True if we have high confidence in name matching
        return score >= 1.0 and fuzz.partial_ratio(match_name, name) >= ratio

    def fix_url(self, url):
        new_url = url
        if not re.match(r"^https?://", url):
            new_url = "http://" + url
        return new_url
