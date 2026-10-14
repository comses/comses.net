"""
Management command for indexing digest archives based on the contents of https://zenodo.org/communities/comses-digest/records
"""

import logging
import requests
from datetime import datetime
from django.core.management.base import BaseCommand

from home.models import ComsesDigest

logger = logging.getLogger(__name__)

ZENODO_COMMUNITY_API_URL = "https://zenodo.org/api/communities/comses-digest/records"

def iter_zenodo_records(session):
    url = f"{ZENODO_COMMUNITY_API_URL}?page=1&size=25&sort=publication-desc"

    while url:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        page = response.json()

        yield from page["hits"]["hits"]

        url = page.get("links", {}).get("next")

class Command(BaseCommand):
    help = "Update CoMSES digest archives page based on the contents of home/static/digest/"

    def handle(self, *args, **options):
        err_msg = ""

        try:
            with requests.Session() as session:
                zenodo_records = list(iter_zenodo_records(session))
        except requests.RequestException:
            logger.exception("Failed to fetch Zenodo records for CoMSES Digest.")
            return

        ComsesDigest.objects.all().delete()

        for record in zenodo_records:
            try:
                ComsesDigest.objects.create(
                    doi=record["doi"],
                    title=record["metadata"]["title"],
                    volume=int(record["metadata"]["journal"]["volume"]),
                    issue_number=int(record["metadata"]["journal"]["issue"]),
                    publication_date=datetime.strptime(record["metadata"]["publication_date"], "%Y-%m-%d").date(),
                    url=record["links"]["latest_html"],
                )
            except Exception as e:
                err_msg += f"{record['links']['latest_html']}\n"
                logger.error(e)

        if err_msg:
            err_msg = "\n\nFailed to add the following digest records, ensure the metadata is correct:\n\n" + err_msg
            logger.error(err_msg)
        else:
            logger.info(f"\n\nSuccessfully indexed all digest records from Zenodo community.")
