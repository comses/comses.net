import logging

from django.contrib.auth.models import User
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django.models import models

from core.tests.base import HypothesisTestCase, MAX_EXAMPLES
from ..models import MemberProfile

logger = logging.getLogger(__name__)


class MemberProfileTestCase(HypothesisTestCase):

    @settings(max_examples=MAX_EXAMPLES)
    @given(st.lists(models(User), max_size=10))
    def test_member_profile_creation(self, users):
        for user in users:
            self.assertIsNotNone(user.member_profile)
            self.assertIsInstance(user.member_profile, MemberProfile)
