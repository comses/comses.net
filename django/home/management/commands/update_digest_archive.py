"""
Management command for indexing digest archives based on the contents of https://zenodo.org/communities/comses-digest/records
"""

import logging
import re
import requests
from datetime import datetime
from django.core.management.base import BaseCommand

from home.models import ComsesDigest

logger = logging.getLogger(__name__)

ZENODO_COMMUNITY_API_URL = "https://zenodo.org/api/communities/comses-digest/records"


class Command(BaseCommand):
    help = "Update CoMSES digest archives page based on the contents of home/static/digest/"

    def handle(self, *args, **options):
        ComsesDigest.objects.all().delete()
        err_msg = ""

        response = requests.get(ZENODO_COMMUNITY_API_URL, params={"size": 1000, "sort": "publication-desc"})
        if response.status_code != 200:
            logger.error("Failed to fetch Zenodo records for CoMSES Digest.")
            return

        zenodo_records = response.json()["hits"]["hits"]
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
                err_msg += f"{record["links"]["latest_html"]}\n"
                logger.error(e)

        if err_msg:
            err_msg = (
                "\n\nFailed to add the following digest records, ensure the metadata is correct:\n\n"
                + err_msg
            )
            logger.error(err_msg)
        else:
            logger.info(f"\n\nSuccessfully indexed all digest records from Zenodo community.")
