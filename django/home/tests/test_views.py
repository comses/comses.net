import logging

from rest_framework.test import APIClient

from django.urls import reverse
from django.test import TestCase

from core.tests.base import UserFactory
from core.tests.permissions_base import BaseViewSetTestCase
from home.views import JobViewSet, EventViewSet
from .base import JobFactory, EventFactory

logger = logging.getLogger(__name__)


class JobViewSetTestCase(BaseViewSetTestCase):
    _view = JobViewSet

    def setUp(self):
        self.user_factory = UserFactory()
        submitter = self.user_factory.create(username='submitter')
        self.instance_factory = JobFactory(submitter=submitter)
        self.create_representative_users(submitter)
        self.instance = self.instance_factory.create()

    def test_retrieve(self):
        self.check_retrieve()

    def test_destroy(self):
        self.check_destroy()

    def test_update(self):
        self.check_update()

    def test_create(self):
        self.check_create()

    def test_list(self):
        self.check_list()


class EventViewSetTestCase(BaseViewSetTestCase):
    _view = EventViewSet

    def setUp(self):
        self.user_factory = UserFactory()
        submitter = self.user_factory.create(username='submitter')
        self.instance_factory = EventFactory(submitter=submitter)
        self.create_representative_users(submitter)
        self.instance = self.instance_factory.create()

    def test_retrieve(self):
        self.check_retrieve()

    def test_destroy(self):
        self.check_destroy()

    def test_update(self):
        self.check_update()

    def test_create(self):
        self.check_create()

    def test_list(self):
        self.check_list()


class JobPageRenderTestCase(TestCase):
    client_class = APIClient

    def setUp(self):
        user_factory = UserFactory()
        self.submitter = user_factory.create(username='submitter')
        job_factory = JobFactory(submitter=self.submitter)
        self.job = job_factory.create()

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
        self.submitter = user_factory.create(username='submitter')
        event_factory = EventFactory(submitter=self.submitter)
        self.event = event_factory.create()

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
        self.profile.personal_url = 'https://geocities.com/{}'.format(self.submitter.username)
        self.profile.save()

    def test_detail(self):
        response = self.client.get(reverse('home:profile-detail', kwargs={'username': self.submitter.username}))
        self.assertEqual(response.status_code, 200)

    def test_list(self):
        response = self.client.get(reverse('home:profile-list'))
        self.assertEqual(response.status_code, 200)
