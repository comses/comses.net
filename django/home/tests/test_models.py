import logging

from hypothesis import given, settings

from core.tests.base import HypothesisTestCase, MAX_EXAMPLES, generate_user

logger = logging.getLogger(__name__)


class MemberProfileTestCase(HypothesisTestCase):

    @settings(max_examples=MAX_EXAMPLES)
    @given(generate_user())
    def test_member_profile_creation(self, user):
        member_profile = user.member_profile
        self.assertTrue(str(user.pk) in member_profile.get_absolute_url())
        self.assertFalse(member_profile.full_member)
        # empty fields
        self.assertFalse(member_profile.personal_url)
        self.assertFalse(member_profile.professional_url)
        self.assertFalse(str(member_profile.bio))
        # nullable fields
        self.assertIsNone(member_profile.avatar_url)
        self.assertIsNone(member_profile.orcid_url)
        self.assertIsNone(member_profile.github_url)
        self.assertIsNone(member_profile.institution)
