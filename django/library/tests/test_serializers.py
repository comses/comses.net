from django.contrib.auth.models import User

from .base import BaseModelTestCase
from ..models import Codebase
from ..serializers import ContributorSerializer, ReleaseContributorSerializer


class SerializerTestCase(BaseModelTestCase):
    def create_raw_user(self):
        username = 'foo.bar'
        User.objects.get_or_create(username=username)
        return {
            'institution_name': 'SHESC',
            'institution_url': 'http://shesc.asu.edu',
            'username': username
        }

    def create_raw_contributor(self):
        return {
            'affiliations': [],
            'email': 'a@b.com',
            'family_name': 'Bar',
            'given_name': 'Foo',
            'middle_name': '',
            # 'name': 'Foo Bar',
            'type': 'person',
            'user': self.create_raw_user()
        }

    def create_raw_release_contributor(self, index=None):
        raw_release_contributor = {
            'contributor': self.create_raw_contributor(),
            'include_in_citation': True,
            'roles': ['author']
        }

        if index is None:
            return raw_release_contributor
        else:
            raw_release_contributor['index'] = index
            return raw_release_contributor

    def test_contributor_save(self):
        raw_contributor = self.create_raw_contributor()
        contributor_serializer = ContributorSerializer(data=raw_contributor)
        contributor_serializer.is_valid(raise_exception=True)
        contributor = contributor_serializer.save()
        self.assertEqual(contributor.email, raw_contributor['email'])

    def test_release_contributor_save(self):
        codebase = Codebase.objects.create(title='Test codebase',
                                           description='Test codebase description',
                                           identifier='1',
                                           submitter=self.user)
        codebase_release = codebase.import_release(submitter=self.user)

        raw_release_contributor = self.create_raw_release_contributor(index=0)
        release_contributor_serializer = ReleaseContributorSerializer(data=raw_release_contributor,
                                                                      context={'release_id': codebase_release.id})
        release_contributor_serializer.is_valid(raise_exception=True)
        release_contributor = release_contributor_serializer.save()
        self.assertEqual(release_contributor.roles, raw_release_contributor['roles'])

    def test_multiple_release_contributor_save(self):
        codebase = Codebase.objects.create(title='Test codebase',
                                           description='Test codebase description',
                                           identifier='1',
                                           submitter=self.user)
        codebase_release = codebase.import_release(submitter=self.user)

        raw_release_contributors = [self.create_raw_release_contributor(index=1),
                                    self.create_raw_release_contributor(index=None)]

        release_contributors_serializer = ReleaseContributorSerializer(many=True,
                                                                       data=raw_release_contributors,
                                                                       context={'release_id': codebase_release.id})
        release_contributors_serializer.is_valid(raise_exception=True)
        release_contributors = release_contributors_serializer.save()

        self.assertEqual(release_contributors[0].index, 0)
        self.assertEqual(release_contributors[1].index, 1)
