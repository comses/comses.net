import logging
from datetime import date

from django.db import models
from django.db.models import Sum, F, Max
from django.db.models.functions import ExtractYear
from django.db import transaction

from wagtail.contrib.search_promotions.models import QueryDailyHits
from wagtail.search.utils import MAX_QUERY_STRING_LENGTH

logger = logging.getLogger(__name__)


class ArchivedQueryHits(models.Model):
    year = models.IntegerField()
    query_string = models.CharField(max_length=MAX_QUERY_STRING_LENGTH)
    hits = models.IntegerField()
    last_updated = models.DateField()

    @classmethod
    def archive_from_daily_hits(cls):
        # get the last date we updated the archive
        last_updated = (
            cls.objects.aggregate(Max("last_updated"))["last_updated__max"] or date.min
        )

        logger.info("Archiving search query hits, last updated: %s", last_updated)

        # group hits by year and query string, filtering out any that have already been archived
        aggregated_hits = (
            QueryDailyHits.objects.filter(date__gt=last_updated)
            .annotate(year=ExtractYear("date"), query_string=F("query__query_string"))
            .values("year", "query_string")
            .annotate(total_hits=Sum("hits"), max_date=Max("date"))
            .order_by("year", "query_string")
        )

        for entry in aggregated_hits:
            cls.create_or_update(entry)

    @classmethod
    @transaction.atomic
    def create_or_update(cls, entry):
        try:
            # update existing record
            obj = cls.objects.get(
                year=entry["year"],
                query_string=entry["query_string"],
            )
            obj.hits = F("hits") + entry["total_hits"]

        except cls.DoesNotExist:
            # create a new record
            obj = cls(
                year=entry["year"],
                query_string=entry["query_string"],
                hits=entry["total_hits"],
                last_updated=entry["max_date"],
            )

        obj.last_updated = entry["max_date"]
        obj.save()
