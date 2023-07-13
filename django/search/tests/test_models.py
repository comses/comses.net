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

        today = datetime.date.today()
        self.date1 = today - datetime.timedelta(days=10)
        self.date2 = today - datetime.timedelta(days=5)

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
            query_string=self.query1.query_string
        )
        self.assertEqual(archived_hits_query1.hits, Q1_HITS)
        self.assertEqual(archived_hits_query1.last_updated, self.date2)

        archived_hits_query2 = ArchivedQueryHits.objects.get(
            query_string=self.query2.query_string
        )
        self.assertEqual(archived_hits_query2.hits, Q2_HITS)
        self.assertEqual(archived_hits_query2.last_updated, self.date2)

    def test_archive_from_daily_hits_no_double_counting(self):
        ArchivedQueryHits.archive_from_daily_hits()
        ArchivedQueryHits.archive_from_daily_hits()

        # hits from date2 should not be counted twice
        archived_hits_query1 = ArchivedQueryHits.objects.get(
            query_string=self.query1.query_string
        )
        self.assertEqual(archived_hits_query1.hits, Q1_HITS)

        archived_hits_query2 = ArchivedQueryHits.objects.get(
            query_string=self.query2.query_string
        )
        self.assertEqual(archived_hits_query2.hits, Q2_HITS)

    def test_archive_from_daily_hits_update(self):
        today = datetime.date.today()

        for _ in range(10):
            self.query1.add_hit(today)
        for _ in range(5):
            self.query2.add_hit(today)

        ArchivedQueryHits.archive_from_daily_hits()

        archived_hits_query1 = ArchivedQueryHits.objects.get(
            query_string=self.query1.query_string
        )
        self.assertEqual(archived_hits_query1.hits, Q1_HITS + 10)
        self.assertEqual(archived_hits_query1.last_updated, today)

        archived_hits_query2 = ArchivedQueryHits.objects.get(
            query_string=self.query2.query_string
        )
        self.assertEqual(archived_hits_query2.hits, Q2_HITS + 5)
        self.assertEqual(archived_hits_query2.last_updated, today)
