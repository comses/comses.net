import logging

from hypothesis import given, settings

from .base import HypothesisTestCase, generate_user, MAX_EXAMPLES

logger = logging.getLogger(__name__)


class EmailAuthenticationBackendTestCase(HypothesisTestCase):

    @settings(max_examples=MAX_EXAMPLES)
    @given(generate_user(username='roman', password='berlioz'))
    def test_email_authentication(self, user):
        response = self.post(view_name='account_login', post_data={'username': user.email, 'password': 'testing'})
        self.assertEquals(response.status_code, 200)
        response = self.post(view_name='account_login', post_data={'username': user.email, 'password': 'berlioz'})
        self.assertEquals(response.status_code, 200)
        # FIXME: validate response for successful authentication?
        self.assertFalse(self.client.login(username=user.email, password='testing'))
        self.assertFalse(self.client.login(username=user.email, password='testing'))
        self.assertTrue(self.client.login(username=user.username, password='berlioz'))
        # self.assertTrue(self.client.login(username=user.email, password='berlioz'))
