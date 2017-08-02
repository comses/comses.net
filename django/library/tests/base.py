from django.contrib.auth.models import User
from django.test import TestCase


class BaseModelTestCase(TestCase):
    def setUp(self):
        self.user = self.create_user()

    def create_user(self, username='test_user', password='test', email='testuser@mailinator.com', **kwargs):
        return User.objects.create_user(username=username, password=password, **kwargs)
