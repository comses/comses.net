from datetime import datetime, timedelta

from django.test import override_settings

from core.models import Event, Job
from core.tests.base import BaseModelTestCase
from home.feeds import ForumFeed, ReviewedModelFeed, EventFeed, JobFeed, YouTubeFeed
from library.models import CodebaseRelease, PeerReview
from library.tests.base import CodebaseFactory

import logging

logger = logging.getLogger(__name__)


@override_settings(DISCOURSE_BASE_URL="https://staging-discourse.comses.net")
class LandingPageFeedsTestCase(BaseModelTestCase):

    def setUp(self):
        super().setUp()
        # create event and job objects for testing
        self.events = [
            self.create_event(
                title="Test Event 1",
                description="This is a test event description.",
                start_date=datetime.now() + timedelta(days=42),
                submitter=self.user,
            )
            for _ in range(5)
        ]
        self.jobs = [
            self.create_job(
                title="Test Job 1",
                description="This is a test job description.",
                external_url="https://example.com/jobbers",
                submitter=self.user,
            )
            for _ in range(5)
        ]
        # setup example codebases
        self.codebase_factory = CodebaseFactory(self.user)
        self.codebases = [
            self.codebase_factory.create_published_release(
                title=f"Test Codebase {i}",
                description="This is a test codebase description.",
                submitter=self.user,
            )
            for i in range(5)
        ]
        # review some releases
        for release in self.codebases[:3]:
            review = PeerReview.objects.create(
                codebase_release=release,
                submitter=self.user.member_profile,
            )
            review.set_complete_status(self.user.member_profile)

    def _verify_feed_item(self, feed_item):
        """validate the structure of a feed item
        TODO: tests should introspect on contents as well."""
        self.assertIn("title", feed_item, "Feed item should contain 'title'")
        self.assertIn("summary", feed_item, "Feed item should contain 'summary'")
        self.assertIn("link", feed_item, "Feed item should contain 'link'")
        self.assertIn("date", feed_item, "Feed item should contain 'date'")

    def _verify_feed_structure(self, feed, expected_item_count=None):
        feed_items = feed.items()
        if expected_item_count is None:
            expected_item_count = feed.max_number_of_items
        else:
            expected_item_count = min(expected_item_count, feed.max_number_of_items)
        self.assertEqual(
            len(feed_items),
            expected_item_count,
            f"{feed} should have {expected_item_count} items",
        )
        logger.debug("Feed items: %s", feed_items)
        for feed_item in feed_items:
            self._verify_feed_item(feed_item)

    def test_forum_feed(self):
        self._verify_feed_structure(ForumFeed(mock=True))

    def test_reviewed_model_feed(self):
        self._verify_feed_structure(ReviewedModelFeed(), CodebaseRelease.objects.reviewed().count())

    def test_event_feed(self):
        self._verify_feed_structure(EventFeed(), Event.objects.count())

    def test_job_feed(self):
        self._verify_feed_structure(JobFeed(), Job.objects.count())

    # FIXME: skipped until there is a mock YT api response
    # def test_youtube_feed(self):
    #     self._verify_feed_structure(YouTubeFeed())
