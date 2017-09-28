import logging

from rest_framework.test import APIClient

from datetime import datetime
from django.contrib.auth.models import User
from django.urls import reverse
from django.test import TestCase
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra.datetime import datetimes
from hypothesis.extra.django.models import models

from core.tests.base import ViewSetTestCase, text, MAX_EXAMPLES, generate_user, UserFactory
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
    @given(generate_job_data(), st.sampled_from(('add', 'change', 'view')))
    def test_add_change_view(self, data, action):
        users, job = data
        owner, user = users

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
    @given(generate_event_data(), st.sampled_from(('add', 'change', 'view')))
    def test_add_change_view(self, data, action):
        users, event = data
        owner, user = users

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


class JobPageRenderTestCase(TestCase):
    client_class = APIClient

    def setUp(self):
        user_factory = UserFactory()
        self.submitter = user_factory.create()
        self.job = Job.objects.create(
            title='PostDoc in ABM',
            description='PostDoc in ABM at ASU',
            date_created=datetime.now(),
            submitter=self.submitter)

    def test_detail(self):
        response = self.client.get(reverse('home:job-detail', kwargs={'pk': self.job.id}))
        self.assertEqual(response.status_code, 200)

    def test_list(self):
        response = self.client.get(reverse('home:job-list'))
        self.assertEqual(response.status_code, 200)


class EventPageRenderTestCase(TestCase):
    client_class = APIClient

    def setUp(self):
        user_factory = UserFactory()
        self.submitter = user_factory.create()
        self.event = Event.objects.create(
            title='CoMSES Conference',
            description='Online Conference',
            start_date=datetime.now(),
            submitter=self.submitter)

    def test_detail(self):
        response = self.client.get(reverse('home:event-detail', kwargs={'pk': self.event.id}))
        self.assertEqual(response.status_code, 200)

    def test_list(self):
        response = self.client.get(reverse('home:event-list'))
        self.assertEqual(response.status_code, 200)

    def test_calendar(self):
        response = self.client.get(reverse('home:event-calendar'))
        self.assertEqual(response.status_code, 200)


class ProfilePageRenderTestCase(TestCase):
    client_class = APIClient

    def setUp(self):
        user_factory = UserFactory()
        self.submitter = user_factory.create()
        self.profile = self.submitter.member_profile
        self.profile.project_url ='https://geocities.com/{}'.format(self.submitter.username)
        self.profile.save()

    def test_detail(self):
        response = self.client.get(reverse('home:profile-detail', kwargs={'username': self.submitter.username}))
        self.assertEqual(response.status_code, 200)

    def test_list(self):
        response = self.client.get(reverse('home:profile-list'))
        self.assertEqual(response.status_code, 200)