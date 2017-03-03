from django.contrib.auth.models import Group, User, Permission
from hypothesis.extra.django.models import models
from hypothesis import strategies as st
from hypothesis.extra.datetime import datetimes
from hypothesis import given, settings
from ..models import Job, Event, MemberProfile
from ..serializers import JobSerializer, EventSerializer
from ..views import JobViewSet, EventViewSet
from core.test_helpers.view import ViewSetTestCase, letters, MAX_EXAMPLES

import logging

logger = logging.getLogger(__name__)


def generate_with_user(username):
    return models(User,
                  username=st.just(str(username)),
                  email=st.just(str(username) + "@comses.net")) \
        .flatmap(
        lambda user: st.tuples(st.just(user), models(MemberProfile, user=st.just(user), affiliations=st.just([]))))


def generate_with_job(submitter):
    return models(Job,
                  title=letters(),
                  description=letters(),
                  date_created=datetimes(min_year=2000, max_year=2017),
                  submitter=st.just(submitter))


@st.composite
def generate_job_data(draw):
    visitors = draw(models(Group))
    usernames = ['0000000000',
                 '0000000001']  # draw(st.lists(st.text(min_size=10, max_size=20), unique=True, min_size=2, max_size=2))
    user_profiles = [draw(generate_with_user(username)) for username in usernames]
    users, profiles = zip(*user_profiles)
    visitors.permissions = Permission.objects.filter(codename__startswith='view_')
    visitors.user_set = User.objects.all()
    job = draw(generate_with_job(users[0]))
    return profiles, job


def generate_with_event(submitter):
    return models(Event,
                  title=letters(),
                  description=letters(),
                  location=letters(),
                  date_created=datetimes(min_year=2000, max_year=2017),
                  early_registration_deadline=datetimes(min_year=2000, max_year=2017),
                  submission_deadline=datetimes(min_year=2000, max_year=2017),
                  start_date=datetimes(min_year=2000, max_year=2017),
                  end_date=datetimes(min_year=2000, max_year=2017),
                  submitter=st.just(submitter))


@st.composite
def generate_event_data(draw):
    visitors = draw(models(Group))
    usernames = draw(st.lists(st.text(min_size=10, max_size=20), unique=True, min_size=2, max_size=2))
    # logger.debug(usernames)
    user_profiles = [draw(generate_with_user(username)) for username in usernames]
    users, profiles = zip(*user_profiles)
    visitors.permissions = Permission.objects.filter(codename__startswith='view_')
    visitors.user_set = User.objects.all()
    event = draw(generate_with_event(users[0]))
    return profiles, event


class JobViewsetTestCase(ViewSetTestCase):
    model_cls = Job
    modelviewset_cls = JobViewSet
    serializer_cls = JobSerializer
    detail_url_name = 'home:job-detail'
    list_url_name = 'home:job-list'

    @settings(max_examples=MAX_EXAMPLES)
    @given(generate_job_data(), st.sampled_from(('change', 'add', 'view')))
    def test_add_change_view(self, data, action):
        profiles, job = data
        owner, user = profiles

        self.check_authorization(action, owner, job)
        self.check_authorization(action, user, job)

    @settings(max_examples=MAX_EXAMPLES)
    @given(generate_job_data())
    def test_delete(self, data):
        profiles, job = data
        owner, user = profiles

        self.check_authorization('delete', owner, job)
        job.save()
        self.check_authorization('delete', user, job)

    @settings(max_examples=MAX_EXAMPLES, perform_health_check=False)
    @given(generate_job_data())
    def test_anonymous(self, data):
        profiles, job = data

        self.check_anonymous_authorization(job)


class EventViewSetTestCase(ViewSetTestCase):
    model_cls = Event
    modelviewset_cls = EventViewSet
    serializer_cls = EventSerializer
    detail_url_name = 'home:event-detail'
    list_url_name = 'home:event-list'

    @settings(max_examples=MAX_EXAMPLES)
    @given(generate_event_data(), st.sampled_from(('change', 'add', 'view')))
    def test_add_change_view(self, data, action):
        profiles, event = data
        owner, user = profiles

        self.check_authorization(action, owner, event)
        self.check_authorization(action, user, event)

    @settings(max_examples=MAX_EXAMPLES)
    @given(generate_event_data())
    def test_delete(self, data):
        profiles, event = data
        owner, user = profiles

        self.check_authorization('delete', owner, event)
        event.save()
        self.check_authorization('delete', user, event)

    @settings(max_examples=MAX_EXAMPLES)
    @given(generate_event_data())
    def test_anonymous(self, data):
        profiles, event = data

        self.check_anonymous_authorization(event)
