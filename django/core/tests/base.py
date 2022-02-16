import logging
import os
import shlex
import shutil
import subprocess

from django.conf import settings
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


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
