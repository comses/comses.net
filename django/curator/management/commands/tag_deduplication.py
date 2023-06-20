import csv
import logging
import os
from datetime import date

import pytz
from dateutil.parser import parse as parse_date
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Count, Max

from core.models import MemberProfile, Job, Event
from library.models import (
    CodebaseReleaseDownload,
    CodebaseRelease,
    Codebase,
    PeerReview,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Deduplicate tags and map tags to canonical list"

    def add_arguments(self, parser):
        parser.add_argument(
            "--from", help="isoformat start date (yyyy-mm-dd) e.g., --from 2018-03-15"
        )
        parser.add_argument(
            "--to",
            help="isoformat end date (yyyy-mm-dd) e.g., --to 2018-06-01. Blank defaults to today.",
            default=None,
        )
        parser.add_argument(
            "--directory",
            "-d",
            help="directory to store statistics in",
            default="/shared/statistics",
        )
        parser.add_argument(
            "--aggregations",
            "-a",
            default="release,codebase,ip,new,reviewed,summary",
            help="comma separated list of things to aggregate, default is release, codebase, ip, new, reviewed, users",
        )
