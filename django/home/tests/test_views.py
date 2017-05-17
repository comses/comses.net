import logging

from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra.datetime import datetimes
from hypothesis.extra.django.models import models

from core.tests.base import ViewSetTestCase, text, MAX_EXAMPLES, generate_user
from core.models import Event, Job
from home.serializers import JobSerializer, EventSerializer
from home.views import JobViewSet, EventViewSet

logger = logging.getLogger(__name__)


def generate_with_job(submitter):
    return models(Job,
                  title=text(),
                  description=text(),
                  summary=text(),
                  date_created=datetimes(min_year=2000, max_year=2017),
                  submitter=st.just(submitter))


@st.composite
def generate_job_data(draw):
    users = [draw(generate_user(username)) for username in ('test1', 'test2')]
    job = draw(generate_with_job(users[0]))
    return users, job


def generate_with_event(submitter):
    return models(Event,
                  description=text(),
                  summary=text(),
                  title=text(),
                  location=text(),
                  date_created=datetimes(min_year=2000, max_year=2017),
                  early_registration_deadline=datetimes(min_year=2000, max_year=2017),
                  submission_deadline=datetimes(min_year=2000, max_year=2017),
                  start_date=datetimes(min_year=2000, max_year=2017),
                  end_date=datetimes(min_year=2000, max_year=2017),
                  submitter=st.just(submitter))


@st.composite
def generate_event_data(draw):
    users = [draw(generate_user(username)) for username in ('test1', 'test2')]
    event = draw(generate_with_event(users[0]))
    return users, event


class JobViewSetTestCase(ViewSetTestCase):
    model_cls = Job
    modelviewset_cls = JobViewSet
    serializer_cls = JobSerializer
    detail_url_name = 'home:job-detail'
    list_url_name = 'home:job-list'

    @settings(max_examples=MAX_EXAMPLES)
    @given(generate_job_data())
    def test_add_change_view(self, data):
        users, job = data
        owner, user = users

        for action in ('change', 'add', 'view'):
            self.check_authorization(action, owner, job)
            self.check_authorization(action, user, job)

    @settings(max_examples=MAX_EXAMPLES)
    @given(generate_job_data())
    def test_delete(self, data):
        users, job = data
        owner, user = users

        self.check_authorization('delete', owner, job)
        job.save()
        self.check_authorization('delete', user, job)

    @settings(max_examples=MAX_EXAMPLES)
    @given(generate_job_data())
    def test_anonymous(self, data):
        users, job = data
        self.check_anonymous_authorization(job)


class EventViewSetTestCase(ViewSetTestCase):
    model_cls = Event
    modelviewset_cls = EventViewSet
    serializer_cls = EventSerializer
    detail_url_name = 'home:event-detail'
    list_url_name = 'home:event-list'

    @settings(max_examples=MAX_EXAMPLES)
    @given(generate_event_data())
    def test_add_change_view(self, data):
        users, event = data
        owner, user = users

        for action in ('change', 'add', 'view'):
            self.check_authorization(action, owner, event)
            self.check_authorization(action, user, event)

    @settings(max_examples=MAX_EXAMPLES)
    @given(generate_event_data())
    def test_delete(self, data):
        users, event = data
        owner, user = users

        self.check_authorization('delete', owner, event)
        event.save()
        self.check_authorization('delete', user, event)

    @settings(max_examples=MAX_EXAMPLES)
    @given(generate_event_data())
    def test_anonymous(self, data):
        profiles, event = data

        self.check_anonymous_authorization(event)