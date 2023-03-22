"""
Management command for indexing digest archives based on the contents of home/static/digest/

Follow the formatting convention of the existing files in home/static/digest/:
e.g. vol11_no3_Spring_2023.pdf
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
        err_msg = ""

        for file_name in os.listdir(DIGEST_STATIC_DIR):
            if file_name.endswith(".pdf"):
                try:
                    self.add_digest_archive(file_name)
                except Exception as e:
                    err_msg += f"{file_name}\n"
                    logger.error(e)
            else:
                logger.info(f"Skipping non-pdf file: {file_name}")

        if err_msg:
            err_msg = (
                "\n\nFailed to add the following digest archives, ensure the file name is correct:\n\n"
                + err_msg
            )
            logger.error(err_msg)
        else:
            logger.info(f"\n\nSuccessfully indexed all pdfs in {DIGEST_STATIC_DIR}")

    def add_digest_archive(self, file_name):
        volume = int(re.search(r"vol(\d+)", file_name, re.IGNORECASE).group(1))
        number = int(re.search(r"no(\d+)", file_name, re.IGNORECASE).group(1))
        year_published = int(re.search(r"(20\d{2})", file_name).group(1))
        season_str = (
            re.search(r"(spring|summer|fall|winter)", file_name, re.IGNORECASE)
            .group(1)
            .lower()
        )
        for _season, label in DigestArchive.Seasons.choices:
            if season_str == label.lower():
                season = _season
                break

        digest = DigestArchive(
            volume=volume,
            number=number,
            year_published=year_published,
            season=season,
            static_path="digest/" + file_name,
        )

        digest.save()
