from django.test import TestCase

from core.tests.base import UserFactory
from curator.models import PendingTagCleanup
from curator.wagtail_hooks import PendingTagCleanupPermissionHelper


class ProcessPendingTagCleanupsTestCase(TestCase):
    def setUp(self):
        self.user_factory = UserFactory()
        self.superuser = self.user_factory.create(is_superuser=True)
        self.user = self.user_factory.create()
        self.pendingtagcleanups = PendingTagCleanup.objects.bulk_create([
            PendingTagCleanup(old_name='foo', new_name='bar'),
            PendingTagCleanup(old_name='foo', new_name='baz')
        ])

    def test_process_pendingtagcleanups_permission(self):
        print(self.superuser.__dict__)
        self.client.login(username=self.user.username, password=self.user_factory.password)

        # Users without process_pendingtagcleanup permission should not be able to use the route
        response = self.client.post(PendingTagCleanup.process_url())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(PendingTagCleanup.objects.filter(transaction_id__isnull=True).count(), 2)

        # Superusers can call the process route to process pending tag cleanups
        self.client.login(username=self.superuser.username, password=self.user_factory.password)
        response = self.client.post(PendingTagCleanup.process_url(), data={'action': 'process'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PendingTagCleanup.objects.filter(transaction_id__isnull=True).count(), 0)

    def test_no_delete_permission_on_inactive_pendingtagcleanups(self):
        pending_tag_cleanup = PendingTagCleanup.objects.get(new_name='bar')
        ph = PendingTagCleanupPermissionHelper(PendingTagCleanup)
        self.assertTrue(pending_tag_cleanup.is_active)
        self.assertTrue(ph.user_can_delete_obj(self.superuser, pending_tag_cleanup))
        pending_tag_cleanup.is_active = False
        self.assertFalse(ph.user_can_delete_obj(self.superuser, pending_tag_cleanup))