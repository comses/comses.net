import logging
import os
import shlex
import shutil
import subprocess
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from hypothesis import strategies as st
from hypothesis.extra import django as hypothesis_django
from hypothesis.extra.django.models import models, add_default_field_mapping

from core.fields import MarkdownField

logger = logging.getLogger(__name__)

MAX_EXAMPLES = 6

add_default_field_mapping(MarkdownField, st.just("# The description"))

DEFAULT_ALPHABET = st.characters(
    whitelist_categories={'Lu', 'Ll', 'Lt', 'Lm', 'Lo'},
    blacklist_characters=(chr(0),)
)


def text(min_size=1, max_size=20):
    return st.text(alphabet=DEFAULT_ALPHABET, min_size=min_size, max_size=max_size)


def dois(**kwargs):
    return st.text(alphabet=DEFAULT_ALPHABET, **kwargs)


def generate_user(username='test_user', password='default.testing.password'):
    return models(User,
                  username=st.just(str(username)),
                  email=st.just(str(username) + "@comses.net"),
                  first_name=text(),
                  last_name=text(),
                  password=st.just(password))


class HypothesisTestCase(hypothesis_django.TestCase):
    def reverse(self, view_name, query_parameters_dict=None):
        reversed_url = reverse(view_name)
        if query_parameters_dict is not None:
            return '%s?%s' % (reversed_url, urlencode(query_parameters_dict))
        return reversed_url

    def _resolve(self, url=None, view_name=None, query_parameters_dict=None):
        if view_name is not None:
            reversed_url = self.reverse(view_name, query_parameters_dict=query_parameters_dict)
            url = reversed_url
        if url is None:
            self.fail("You must pass a URL or view name to access.")
        return url

    def get(self, *args, url=None, view_name=None, query_parameters_dict=None):
        url = self._resolve(url, view_name, query_parameters_dict=query_parameters_dict)
        return self.client.get(url, *args)

    def post(self, *args, url=None, view_name=None, post_data=None):
        url = self._resolve(url, view_name)
        return self.client.post(url, post_data, *args)

    def put(self, *args, url=None, view_name=None, put_data=None):
        url = self._resolve(url, view_name)
        return self.client.put(url, put_data, *args)


def make_user(username='test_user', password='default.testing.password', email='comses.test@mailinator.com'):
    factory = UserFactory()
    return factory.create(username=username, password=password, email=email), factory


class UserFactory:
    def __init__(self, **defaults):
        if not defaults.get('password'):
            defaults['password'] = 'test'
        self.id = 0
        self.password = defaults.get('password')
        self.defaults = {}
        username = defaults.get('username')
        if username:
            self.defaults.update({'username': username})
        email = defaults.get('email')
        if email:
            self.defaults.update({'email': email})

    def extract_password(self, overrides):
        if overrides.get('password'):
            return overrides.pop('password')
        else:
            return self.password

    def get_default_data(self):
        defaults = self.defaults.copy()
        defaults['username'] = defaults.get('username', 'submitter{}'.format(self.id))
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
        if not kwargs.get('email'):
            kwargs['email'] = '{}@gmail.com'.format(kwargs['username'])
        user = User(**kwargs)
        if password:
            user.set_password(password)
        return user


def initialize_test_shared_folders():
    for d in [settings.LIBRARY_ROOT, settings.REPOSITORY_ROOT, settings.BACKUP_ROOT, settings.MEDIA_ROOT]:
        os.makedirs(d, exist_ok=True)

    subprocess.run(shlex.split('borg init --encryption=none {}'.format(settings.BORG_ROOT)), check=True)


def destroy_test_shared_folders():
    shutil.rmtree(settings.SHARE_DIR, ignore_errors=True)
