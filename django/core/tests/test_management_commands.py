from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from core.tests.base import create_test_user


class SyncDiscourseUsersCommandTestCase(TestCase):
    def test_dry_run_lists_active_users_without_syncing(self):
        active_user, _ = create_test_user(username="active-user")
        inactive_user, _ = create_test_user(username="inactive-user")
        inactive_user.is_active = False
        inactive_user.save(update_fields=["is_active"])
        stdout = StringIO()

        with patch(
            "core.management.commands.sync_discourse_users.sync_discourse_sso_user"
        ) as sync_user:
            call_command("sync_discourse_users", "--dry-run", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("Would sync 1 user(s) to Discourse", output)
        self.assertIn(active_user.username, output)
        self.assertNotIn(inactive_user.username, output)
        sync_user.assert_not_called()

    @patch("core.management.commands.sync_discourse_users.sync_discourse_sso_user")
    def test_syncs_filtered_user(self, sync_user):
        target_user, _ = create_test_user(username="target-user")
        other_user, _ = create_test_user(username="other-user")
        sync_user.return_value = True
        stdout = StringIO()

        call_command(
            "sync_discourse_users",
            "--username",
            target_user.username,
            "--delay",
            "0",
            stdout=stdout,
        )

        sync_user.assert_called_once_with(target_user)
        output = stdout.getvalue()
        self.assertIn(f"Synced {target_user.username}", output)
        self.assertNotIn(f"Synced {other_user.username}", output)
