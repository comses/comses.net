from abc import ABC, abstractmethod
import logging
import os
import shlex
import shutil
import subprocess

from datetime import date, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from core.models import Job, Event
from core.serializers import EventSerializer, JobSerializer


logger = logging.getLogger(__name__)

User = get_user_model()


def update_index():
    """rebuild ES indices for tests that need search/pagination"""
    call_command("update_index", verbosity=0)


class ContentModelFactory(ABC):
    def __init__(self, submitter):
        self.submitter = submitter

    @property
    @abstractmethod
    def model(self):
        pass

    @property
    @abstractmethod
    def serializer(self):
        pass

    @abstractmethod
    def get_default_data(self) -> dict:
        pass

    def get_request_data(
        self, with_tags=True, honeypot_value=None, elapsed_time=999, **kwargs
    ):
        data = self.get_default_data()
        data.pop("submitter")
        if with_tags:
            data["tags"] = []
        if not hasattr(self.model, "spam_moderation"):
            return data

        if honeypot_value:
            data["content"] = honeypot_value
        data["loaded_time"] = timezone.now() - timezone.timedelta(seconds=elapsed_time)
        data.update(kwargs)
        return data

    def create(self, **overrides):
        content = self.create_unsaved(**overrides)
        content.save()
        return content

    def get_or_create(self, **kwargs):
        return self.model.objects.get_or_create(**kwargs)

    def create_unsaved(self, **overrides):
        kwargs = self.get_default_data()
        kwargs.update(overrides)
        return self.model(**kwargs)

    def data_for_create_request(self, **overrides):
        content = self.create(**overrides)
        return self.serializer(content).data


class JobFactory(ContentModelFactory):
    model = Job
    serializer = JobSerializer

    def get_default_data(self):
        return {
            "title": "PostDoc in ABM",
            "description": "PostDoc in ABM at ASU",
            "summary": "PostDoc in ABM at ASU",
            "submitter": self.submitter,
        }


class EventFactory(ContentModelFactory):
    model = Event
    serializer = EventSerializer

    def get_default_data(self):
        return {
            "title": "CoMSES Conference",
            "description": "Online Conference",
            "summary": "Online Conference",
            "location": "Your computer",
            "submitter": self.submitter,
            "start_date": date.today() + timedelta(days=1),
        }


def create_test_user(
    username="test_user", email="comses.test@mailinator.com", **kwargs
):
    factory = UserFactory(username=username, email=email, **kwargs)
    return factory.create(), factory


class UserFactory:
    def __init__(self, **defaults):
        self.next_user_id = 0
        self.password = defaults.pop("password", "testing-password")
        self.defaults = defaults.copy()

    def extract_password(self, overrides):
        if "password" in overrides:
            return overrides.pop("password")
        else:
            return self.password

    def get_default_data(self, **kwargs):
        defaults = self.defaults.copy()
        # always generate a unique username for the next user
        username = defaults["username"] = defaults.get(
            "username", f"submitter{self.next_user_id}"
        )
        defaults.setdefault("email", f"{username}@example.com")
        defaults.setdefault("username", username)
        self.next_user_id += 1
        defaults.update(kwargs)
        return defaults

    def create(self, **kwargs):
        return self.get_or_create(**kwargs)

    def get_or_create(self, **kwargs):
        password = self.extract_password(kwargs)
        user_data_with_defaults = self.get_default_data(**kwargs)
        """
        if "email" not in kwargs:
            kwargs.update(email=default_data.get('email'))
        if "username" not in kwargs:
            kwargs.update(username=default_data.get("username"))
        """
        user, created = User.objects.get_or_create(**user_data_with_defaults)
        user.set_password(password)
        user.save()
        return user


class BaseModelTestCase(TestCase):
    def setUp(self):
        self.user = self.create_user()
        self.event_factory = EventFactory(self.user)
        self.job_factory = JobFactory(self.user)

    def create_user(self, **kwargs):
        user, factory = create_test_user(**kwargs)
        self.user_factory = factory
        return user

    def create_event(self, **kwargs):
        return self.event_factory.create(**kwargs)

    def create_job(self, **kwargs):
        return self.job_factory.create(**kwargs)


def initialize_test_shared_folders():
    for d in [
        settings.LIBRARY_ROOT,
        settings.REPOSITORY_ROOT,
        settings.BACKUP_ROOT,
        settings.MEDIA_ROOT,
    ]:
        os.makedirs(d, exist_ok=True)

    subprocess.run(
        shlex.split("borg init --encryption=none {}".format(settings.BORG_ROOT)),
        check=True,
    )


def destroy_test_shared_folders():
    shutil.rmtree(settings.SHARE_DIR, ignore_errors=True)
