from ..serializers import ContributorSerializer, CodebaseContributorSerializer, Codebase, CodebaseRelease
from .base import BaseModelTestCase
from home.common_serializers import RelatedMemberProfileSerializer


class SerializerTestCase(BaseModelTestCase):
    def create_raw_user(self):
        return {
            'institution_name': 'SHESC',
            'institution_url': 'http://shesc.asu.edu',
            'username': 'foo.bar'
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

    def create_raw_release_contributor(self):
        return {
            'contributor': self.create_raw_contributor(),
            'include_in_citation': True,
            'index': 0,
            'is_maintainer': False,
            'is_rights_holder': False,
            'role': 'author'
        }

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
        codebase_release = codebase.make_release(submitter=self.user)

        raw_release_contributor = self.create_raw_release_contributor()
        release_contributor_serializer = CodebaseContributorSerializer(data=raw_release_contributor,
                                                                       context={'release_id': codebase_release.id})
        release_contributor_serializer.is_valid(raise_exception=True)
        release_contributor = release_contributor_serializer.save()
        self.assertEqual(release_contributor.role, raw_release_contributor['role'])
