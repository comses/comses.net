import logging

from django.core.management.base import BaseCommand
from wagtail.contrib.search_promotions.models import Query, QueryDailyHits
from search.models import ArchivedQueryHits

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "-d",
            "--expiry-days",
            type=int,
            default=7,
            help="delete all daily hits older than this many days, defaults to 7",
        )
        parser.add_argument(
            "-P",
            "--purge-queries",
            action="store_true",
            help="deletes all queries that have no daily hits after purging",
        )

    def handle(self, *args, **options):
        ArchivedQueryHits.archive_from_daily_hits()

        logger.info(
            "Purging query daily hits older than %d days", options["expiry_days"]
        )
        QueryDailyHits.garbage_collect(days=options["expiry_days"])

        if options["purge_queries"]:
            logger.info("Purging queries that have no daily hits")
            Query.garbage_collect()
