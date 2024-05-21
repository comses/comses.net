from abc import ABC, abstractmethod
import logging
import os
import shlex
import shutil
import subprocess
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from core.models import Job, Event
from core.serializers import EventSerializer, JobSerializer


logger = logging.getLogger(__name__)


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


def make_user(
    username="test_user",
    password="default.testing.password",
    email="comses.test@mailinator.com",
):
    factory = UserFactory()
    return factory.create(username=username, password=password, email=email), factory


class UserFactory:
    def __init__(self, **defaults):
        if not defaults.get("password"):
            defaults["password"] = "test"
        self.id = 0
        self.password = defaults.get("password")
        self.defaults = {}
        username = defaults.get("username")
        if username:
            self.defaults.update({"username": username})
        email = defaults.get("email")
        if email:
            self.defaults.update({"email": email})

    def extract_password(self, overrides):
        if overrides.get("password"):
            return overrides.pop("password")
        else:
            return self.password

    def get_default_data(self):
        defaults = self.defaults.copy()
        defaults["username"] = defaults.get("username", "submitter{}".format(self.id))
        self.id += 1
        return defaults

    def create(self, **overrides):
        user = self.create_unsaved(**overrides)
        user.save()
        return user

    def create_unsaved(self, **overrides):
        password = self.extract_password(overrides)
        kwargs = self.get_default_data()
        kwargs.update(overrides)
        if not kwargs.get("email"):
            kwargs["email"] = "{}@gmail.com".format(kwargs["username"])
        user = User(**kwargs)
        if password:
            user.set_password(password)
        return user


class BaseModelTestCase(TestCase):
    def setUp(self):
        self.user = self.create_user()

    def create_user(self, username="test_user", password="test", **kwargs):
        kwargs.setdefault("email", "testuser@mailinator.com")
        return User.objects.create_user(username=username, password=password, **kwargs)


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
