from django.test import TestCase

from core.tests.base import UserFactory
from curator.models import TagCleanup
from curator.wagtail_hooks import TagCleanupPermissionHelper


class ProcessTagCleanupsTestCase(TestCase):
    def setUp(self):
        self.user_factory = UserFactory()
        self.superuser = self.user_factory.create(is_superuser=True)
        self.user = self.user_factory.create()
        self.tag_cleanups = TagCleanup.objects.bulk_create([
            TagCleanup(old_name='foo', new_name='bar'),
            TagCleanup(old_name='foo', new_name='baz')
        ])

    def test_process_tagcleanups_permission(self):
        self.client.login(username=self.user.username, password=self.user_factory.password)

        # Users without process_tagcleanup permission should not be able to use the route
        response = self.client.post(TagCleanup.process_url())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(TagCleanup.objects.filter(transaction_id__isnull=True).count(), 2)

        # Superusers can call the process route to process tag cleanups
        self.client.login(username=self.superuser.username, password=self.user_factory.password)
        response = self.client.post(TagCleanup.process_url(), data={'action': 'process'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(TagCleanup.objects.filter(transaction_id__isnull=True).count(), 0)

    def test_no_delete_permission_on_inactive_tagcleanups(self):
        tag_cleanup = TagCleanup.objects.get(new_name='bar')
        ph = TagCleanupPermissionHelper(TagCleanup)
        self.assertIsNone(tag_cleanup.transaction_id)
        self.assertTrue(ph.user_can_delete_obj(self.superuser, tag_cleanup))
        TagCleanup.objects.process()
        tag_cleanup = TagCleanup.objects.get(new_name='bar')
        self.assertIsNotNone(tag_cleanup.transaction_id)
        self.assertFalse(ph.user_can_delete_obj(self.superuser, tag_cleanup))