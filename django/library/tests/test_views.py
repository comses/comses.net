from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from hypothesis import given, settings, Verbosity
from hypothesis import strategies as st
from hypothesis.extra.django.models import models
from rest_framework.test import force_authenticate

from core.tests.base import ViewSetTestCase, text, MAX_EXAMPLES, generate_user, UserFactory
from library.models import Codebase
from library.serializers import CodebaseSerializer
from library.views import CodebaseViewSet
from .base import CodebaseFactory, CodebaseReleaseFactory, ContributorFactory, ReleaseContributorFactory


def generate_with_codebase(submitter):
    return models(Codebase,
                  title=text(),
                  description=text(),
                  summary=text(),
                  uuid=st.uuids(),
                  references_text=st.just('References'),
                  associated_publication_text=st.just('Associated publication'),
                  repository_url=st.just('https://example.com'),
                  doi=st.just('10.1126/science.1183532'),
                  media=st.just([]),
                  identifier=text(),
                  relationships=st.just([]),
                  submitter=st.just(submitter),
                  )


@st.composite
@settings(verbosity=Verbosity.verbose)
def generate_codebases(draw):
    users = [draw(generate_user(username)) for username in ('test1', 'test2')]
    codebases = draw(st.lists(generate_with_codebase(users[0]), min_size=2, max_size=2))
    return users, codebases


class CodebaseViewSetTestCase(ViewSetTestCase):
    model_cls = Codebase
    modelviewset_cls = CodebaseViewSet
    serializer_cls = CodebaseSerializer
    detail_url_name = 'library:codebase-detail'
    list_url_name = 'library:codebase-list'

    def create_add_response(self, user: User, data):
        data.pop('id')
        # FIXME: using example() is deprecated
        data['identifier'] = str(st.uuids().example())

        http_method = self.action_http_map['add']
        request_factory = getattr(self.factory, http_method)
        request = request_factory(reverse(self.list_url_name), data=data, format='json')
        force_authenticate(request, user)
        response = self.modelviewset_cls.as_view(
            {'put': 'update', 'get': 'retrieve', 'post': 'create', 'delete': 'destroy'})(request)
        return response

    @settings(max_examples=MAX_EXAMPLES, verbosity=Verbosity.verbose, perform_health_check=False)
    @given(generate_codebases(), st.sampled_from(('add', 'change', 'view')))
    def test_add_change_view(self, data, action):
        users, codebases = data
        owner, user = users

        self.check_authorization(action, owner, codebases[0])
        self.check_authorization(action, user, codebases[0])

    @settings(max_examples=MAX_EXAMPLES)
    @given(generate_codebases())
    def test_delete(self, data):
        users, codebases = data
        owner, user = users

        self.check_authorization('delete', owner, codebases[0])
        self.check_authorization('delete', user, codebases[1])

    @settings(max_examples=MAX_EXAMPLES)
    @given(generate_codebases())
    def test_anonymous(self, data):
        _users, codebases = data
        self.check_anonymous_authorization(codebases[0])


class CodebaseRenderPageTestCase(TestCase):
    def setUp(self):
        user_factory = UserFactory()
        codebase_factory = CodebaseFactory()
        self.submitter = user_factory.create()
        self.codebase = codebase_factory.create(self.submitter)

    def test_list(self):
        response = self.client.get(reverse('library:codebase-detail', kwargs={'identifier': self.codebase.identifier}))
        self.assertTrue(response.status_code, 200)


class CodebaseReleaseRenderPageTestCase(TestCase):
    def setUp(self):
        user_factory = UserFactory()
        codebase_factory = CodebaseFactory()
        contributor_factory = ContributorFactory()
        codebase_release_factory = CodebaseReleaseFactory()

        self.submitter = user_factory.create()
        contributor = contributor_factory.create(user=self.submitter)

        self.codebase = codebase_factory.create(submitter=self.submitter)
        self.codebase_release = codebase_release_factory.create(codebase=self.codebase)
        release_contributor_factory = ReleaseContributorFactory(codebase_release=self.codebase_release)
        release_contributor_factory.create(contributor=contributor)

    def test_detail(self):
        response = self.client.get(reverse('library:codebaserelease-detail',
                                           kwargs={'identifier': self.codebase.identifier,
                                                   'version_number': self.codebase_release.version_number}))
        self.assertTrue(response.status_code, True)
