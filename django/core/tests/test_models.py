import logging
import random
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from core.models import Event, Job
from .base import BaseModelTestCase, JobFactory, EventFactory

logger = logging.getLogger(__name__)


class JobTest(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        self.job_factory = JobFactory(submitter=self.user)
        today = timezone.now()

        self.threshold = settings.EXPIRED_JOB_DAYS_THRESHOLD

        # active jobs
        self.active_job = self.job_factory.create(
            application_deadline=today + timedelta(days=30),
            title="Active Job",
        )
        self.barely_active_job = self.job_factory.create(
            application_deadline=today, title="Barely Active Job"
        )
        self.no_deadline_active_job = self.job_factory.create(
            application_deadline=None,
            date_created=today,
            title="No Deadline Active Job",
        )
        self.no_deadline_barely_active_job = self.job_factory.create(
            application_deadline=None,
            date_created=today - timedelta(days=self.threshold),
            title="No Deadline Barely Active Job",
        )

        # expired jobs
        self.expired_job = self.job_factory.create(
            application_deadline=today - timedelta(days=7),
            title="Expired Job",
        )
        self.barely_expired_job = self.job_factory.create(
            application_deadline=today - timedelta(days=1),
            title="Barely Expired Job",
        )
        expired_post_date = today - timedelta(days=self.threshold + 90)
        self.no_deadline_expired_job = self.job_factory.create(
            application_deadline=None,
            date_created=expired_post_date,
            title="No Deadline Expired Job",
        )
        # manually override last_modified to be expired
        Job.objects.filter(pk=self.no_deadline_expired_job.pk).update(
            last_modified=expired_post_date
        )
        self.no_deadline_active_job.refresh_from_db()
        barely_expired_post_date = today - timedelta(days=self.threshold + 1)
        self.no_deadline_barely_expired_job = self.job_factory.create(
            application_deadline=None,
            date_created=barely_expired_post_date,
            title="No Deadline Barely Expired Job",
        )
        Job.objects.filter(pk=self.no_deadline_barely_expired_job.pk).update(
            last_modified=barely_expired_post_date
        )
        self.no_deadline_barely_active_job.refresh_from_db()

    def test_with_expired(self):
        jobs = Job.objects.all().with_expired()
        for job in jobs:
            if job in [
                self.expired_job,
                self.barely_expired_job,
                self.no_deadline_expired_job,
                self.no_deadline_barely_expired_job,
            ]:
                self.assertTrue(job.is_expired)
            else:
                self.assertFalse(job.is_expired)

    def test_upcoming(self):
        jobs = Job.objects.upcoming()
        for active_jobs in [
            self.active_job,
            self.barely_active_job,
            self.no_deadline_active_job,
            self.no_deadline_barely_active_job,
        ]:
            self.assertIn(active_jobs, jobs)


class EventTest(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        self.event_factory = EventFactory(submitter=self.user)
        now = timezone.now()

        # upcoming events
        self.upcoming_event = self.event_factory.create(
            start_date=now + timedelta(days=7),
            end_date=now + timedelta(days=14),
            title="Upcoming Event",
        )
        self.no_end_date_upcoming_event = self.event_factory.create(
            start_date=now + timedelta(days=1),
            end_date=None,
            title="No End Date Upcoming Event",
        )

        # current events
        self.current_event = self.event_factory.create(
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=1),
            title="Current Event",
        )
        self.no_end_date_current_events = [
            self.event_factory.create(
                start_date=now - timedelta(days=threshold),
                end_date=None,
                title="No End Date Current Event",
            )
            for threshold in range(settings.EXPIRED_EVENT_DAYS_THRESHOLD)
        ]

        # expired events
        self.expired_event = self.event_factory.create(
            start_date=now - timedelta(days=14),
            end_date=now - timedelta(days=7),
            title="Expired Event",
        )
        expired_days_threshold = settings.EXPIRED_EVENT_DAYS_THRESHOLD + 1
        sample_expired_event_thresholds = set(
            random.sample(range(expired_days_threshold, 365), 10)
        )
        sample_expired_event_thresholds.add(
            expired_days_threshold
        )  # always test the edge
        self.no_end_date_expired_events = [
            self.event_factory.create(
                start_date=now - timedelta(days=threshold),
                end_date=None,
                title="No End Date Expired Event",
            )
            for threshold in sample_expired_event_thresholds
        ]

    def test_with_expired(self):
        events = Event.objects.all().with_expired()
        for event in events:
            if event in [self.expired_event] + self.no_end_date_expired_events:
                self.assertTrue(event.is_expired)
            else:
                self.assertFalse(event.is_expired)

    def test_upcoming(self):
        events = Event.objects.upcoming()
        for upcoming_event in [
            self.upcoming_event,
            self.current_event,
        ] + self.no_end_date_current_events:
            self.assertIn(upcoming_event, events)
