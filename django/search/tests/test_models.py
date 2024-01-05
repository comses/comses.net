import datetime
from django.test import TestCase
from wagtail.contrib.search_promotions.models import Query
from search.models import ArchivedQueryHits


Q1_D1_HITS = 99
Q1_D2_HITS = 7
Q1_HITS = Q1_D1_HITS + Q1_D2_HITS
Q2_D1_HITS = 15
Q2_D2_HITS = 25
Q2_HITS = Q2_D1_HITS + Q2_D2_HITS


class TestArchivedQueryHits(TestCase):
    def setUp(self):
        self.query1 = Query.get("acorns")
        self.query2 = Query.get("chestnuts")

        self.year = 2023
        self.date1 = datetime.date(self.year, 1, 1)
        self.date2 = datetime.date(self.year, 1, 10)

        for _ in range(Q1_D1_HITS):
            self.query1.add_hit(self.date1)
        for _ in range(Q1_D2_HITS):
            self.query1.add_hit(self.date2)
        for _ in range(Q2_D1_HITS):
            self.query2.add_hit(self.date1)
        for _ in range(Q2_D2_HITS):
            self.query2.add_hit(self.date2)

    def test_archive_from_daily_hits_create(self):
        ArchivedQueryHits.archive_from_daily_hits()

        archived_hits_query1 = ArchivedQueryHits.objects.get(
            query_string=self.query1.query_string, year=self.year
        )
        self.assertEqual(archived_hits_query1.hits, Q1_HITS)
        self.assertEqual(archived_hits_query1.last_updated, self.date2)

        archived_hits_query2 = ArchivedQueryHits.objects.get(
            query_string=self.query2.query_string, year=self.year
        )
        self.assertEqual(archived_hits_query2.hits, Q2_HITS)
        self.assertEqual(archived_hits_query2.last_updated, self.date2)

    def test_archive_from_daily_hits_no_double_counting(self):
        ArchivedQueryHits.archive_from_daily_hits()
        ArchivedQueryHits.archive_from_daily_hits()

        # hits from date2 should not be counted twice
        archived_hits_query1 = ArchivedQueryHits.objects.get(
            query_string=self.query1.query_string, year=self.year
        )
        self.assertEqual(archived_hits_query1.hits, Q1_HITS)

        archived_hits_query2 = ArchivedQueryHits.objects.get(
            query_string=self.query2.query_string, year=self.year
        )
        self.assertEqual(archived_hits_query2.hits, Q2_HITS)

    def test_archive_from_daily_hits_update(self):
        ArchivedQueryHits.archive_from_daily_hits()

        updated_date = datetime.date(2024, 1, 1)
        self.query1.add_hit(updated_date)
        ArchivedQueryHits.archive_from_daily_hits()

        archived_hits_year1 = ArchivedQueryHits.objects.get(
            query_string=self.query1.query_string, year=self.year
        )
        self.assertEqual(archived_hits_year1.hits, Q1_HITS)
        self.assertEqual(archived_hits_year1.last_updated, self.date2)

        archived_hits_year2 = ArchivedQueryHits.objects.get(
            query_string=self.query1.query_string, year=updated_date.year
        )
        self.assertEqual(archived_hits_year2.hits, 1)
        self.assertEqual(archived_hits_year2.last_updated, updated_date)
