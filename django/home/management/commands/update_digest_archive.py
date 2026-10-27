"""
Management command for indexing digest archives based on the contents of https://zenodo.org/communities/comses-digest/records
"""

import logging
from datetime import datetime

import requests
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction

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


def parse_zenodo_record(record):
    """Extract and validate the fields used to create or update a digest."""
    try:
        doi = record["doi"]
    except (KeyError, TypeError) as exc:
        raise CommandError("Invalid metadata in a Zenodo digest record: DOI is required.") from exc

    if not isinstance(doi, str) or not doi.strip():
        raise CommandError("Invalid metadata in a Zenodo digest record: DOI is required.")

    try:
        metadata = record["metadata"]
        journal = metadata["journal"]
        defaults = {
            "title": metadata["title"],
            "volume": int(journal["volume"]),
            "issue_number": int(journal["issue"]),
            "publication_date": datetime.strptime(metadata["publication_date"], "%Y-%m-%d").date(),
            "url": record["links"]["latest_html"],
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise CommandError(f"Invalid metadata for Zenodo digest record {doi}: {exc}") from exc

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
        except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
            raise CommandError(f"Failed to fetch Zenodo records for CoMSES Digest: {exc}") from exc

        validated_records = [parse_zenodo_record(record) for record in zenodo_records]

        try:
            with transaction.atomic():
                for doi, defaults in validated_records:
                    ComsesDigest.objects.update_or_create(doi=doi, defaults=defaults)
        except DatabaseError as exc:
            raise CommandError("Failed to import Zenodo records for CoMSES Digest.") from exc

        logger.info("Successfully indexed all digest records from Zenodo community.")
