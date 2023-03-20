"""
Management command for indexing digest archives based on the contents of home/static/digest/

Follow the formatting convention of the existing files in home/static/digest/ ensure that it contains:
- the season (Spring, Summer, Fall, Winter)
- the year (e.g. 2023)
- the volume (e.g. v1, vol1, volume1)
- the number (e.g. n1, no1, num1, number1)
"""

import logging
import os
import re
from django.core.management.base import BaseCommand
from home.models import DigestArchive

logger = logging.getLogger(__name__)

DIGEST_STATIC_DIR = "home/static/digest/"


class Command(BaseCommand):
    help = "Update CoMSES digest archives page based on the contents of home/static/digest/"

    def handle(self, *args, **options):
        DigestArchive.objects.all().delete()

        for file_name in os.listdir(DIGEST_STATIC_DIR):
            if file_name.endswith(".pdf"):
                try:
                    self.add_digest_archive(file_name)
                except Exception as e:
                    logger.error(
                        f"Failed to add digest archive: {file_name}, ensure the file name is correct"
                    )
                    logger.error(e)
            else:
                logger.info(f"Skipping non-pdf file: {file_name}")

    def add_digest_archive(self, file_name):
        volume = int(
            re.search(r"(?:v|vol|volume)(\d+)", file_name, re.IGNORECASE).group(1)
        )
        number = int(
            re.search(r"(?:n|no|num|number)(\d+)", file_name, re.IGNORECASE).group(1)
        )
        year_published = int(re.search(r"(20\d{2})", file_name).group(1))
        season_str = (
            re.search(r"(spring|summer|fall|winter)", file_name, re.IGNORECASE)
            .group(1)
            .lower()
        )
        match season_str:
            case "spring":
                season = DigestArchive.Seasons.SPRING
            case "summer":
                season = DigestArchive.Seasons.SUMMER
            case "fall":
                season = DigestArchive.Seasons.FALL
            case "winter":
                season = DigestArchive.Seasons.WINTER

        digest = DigestArchive(
            volume=volume,
            number=number,
            year_published=year_published,
            season=season,
            static_path="digest/" + file_name,
        )

        digest.save()
