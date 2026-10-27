"""
Management command for indexing digest archives based on the contents of https://zenodo.org/communities/comses-digest/records
"""

import logging
from datetime import datetime

import requests
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

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


def validate_zenodo_record(record):
    try:
        doi = record["doi"]
        defaults = {
            "title": record["metadata"]["title"],
            "volume": int(record["metadata"]["journal"]["volume"]),
            "issue_number": int(record["metadata"]["journal"]["issue"]),
            "publication_date": datetime.strptime(record["metadata"]["publication_date"], "%Y-%m-%d").date(),
            "url": record["links"]["latest_html"],
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise CommandError("Invalid metadata in a Zenodo digest record.") from exc

    if not isinstance(doi, str) or not doi.strip():
        raise CommandError("Invalid metadata in a Zenodo digest record: DOI is required.")

    try:
        ComsesDigest(doi=doi, **defaults).full_clean(validate_unique=False)
    except ValidationError as exc:
        raise CommandError(f"Invalid metadata for Zenodo digest record {doi}: {exc}") from exc

    return doi, defaults


class Command(BaseCommand):
    help = "Update CoMSES digest archives from the Zenodo community"

    def handle(self, *args, **options):
        try:
            with requests.Session() as session:
                zenodo_records = list(iter_zenodo_records(session))
        except Exception as exc:
            raise CommandError("Failed to fetch Zenodo records for CoMSES Digest.") from exc

        validated_records = [validate_zenodo_record(record) for record in zenodo_records]

        try:
            with transaction.atomic():
                for doi, defaults in validated_records:
                    ComsesDigest.objects.update_or_create(doi=doi, defaults=defaults)
        except Exception as exc:
            raise CommandError("Failed to import Zenodo records for CoMSES Digest.") from exc

        logger.info("Successfully indexed all digest records from Zenodo community.")
