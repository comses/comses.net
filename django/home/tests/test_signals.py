from unittest.mock import Mock, patch

from django.test import TestCase, override_settings

from core.settings.defaults import Environment
from core.tests.base import create_test_user


@override_settings(
    DEPLOY_ENVIRONMENT=Environment.PRODUCTION,
    DISCOURSE_SSO_SECRET="secret",
)
class DiscourseSignalTestCase(TestCase):
    @patch("home.signals.sync_discourse_user")
    def test_member_profile_save_without_update_fields_syncs_discourse_user(
        self, sync_user
    ):
        sync_user.return_value = Mock(
            json=Mock(return_value={"success": True}),
            raise_for_status=Mock(),
        )
        user, _ = create_test_user(username="sync signal user")
        sync_user.reset_mock()

        user.member_profile.bio = "Updated bio"
        user.member_profile.save()

        sync_user.assert_called_once_with(user)

    @patch("home.signals.sync_discourse_user")
    def test_short_uuid_save_syncs_discourse_user(self, sync_user):
        sync_user.return_value = Mock(
            json=Mock(return_value={"success": True}),
            raise_for_status=Mock(),
        )
        user, _ = create_test_user(username="short uuid user")
        sync_user.reset_mock()

        user.member_profile.short_uuid = "abc123"
        user.member_profile.save(update_fields=["short_uuid"])

        sync_user.assert_called_once_with(user)

    @patch("home.signals.sync_discourse_user")
    def test_picture_save_syncs_discourse_user(self, sync_user):
        sync_user.return_value = Mock(
            json=Mock(return_value={"success": True}),
            raise_for_status=Mock(),
        )
        user, _ = create_test_user(username="picture user")
        sync_user.reset_mock()

        user.member_profile.picture = None
        user.member_profile.save(update_fields=["picture"])

        sync_user.assert_called_once_with(user)

    @patch("home.signals.sync_discourse_user")
    def test_non_payload_field_save_does_not_resync_discourse_user(self, sync_user):
        user, _ = create_test_user(username="non payload user")
        sync_user.reset_mock()

        user.member_profile.bio = "Updated bio"
        user.member_profile.save(update_fields=["bio"])

        sync_user.assert_not_called()

    @patch("home.signals.sync_discourse_user")
    def test_user_email_change_syncs_discourse_user(self, sync_user):
        sync_user.return_value = Mock(
            json=Mock(return_value={"success": True}),
            raise_for_status=Mock(),
        )
        user, _ = create_test_user(username="email change user")
        sync_user.reset_mock()

        user.email = "newemail@example.com"
        user.save(update_fields=["email"])

        sync_user.assert_called_once_with(user)

    @patch("home.signals.sync_discourse_user")
    def test_user_username_change_syncs_discourse_user(self, sync_user):
        sync_user.return_value = Mock(
            json=Mock(return_value={"success": True}),
            raise_for_status=Mock(),
        )
        user, _ = create_test_user(username="username change user")
        sync_user.reset_mock()

        user.username = "changed_username"
        user.save(update_fields=["username"])

        sync_user.assert_called_once_with(user)

    @patch("home.signals.sync_discourse_user")
    def test_user_non_payload_field_change_does_not_sync_discourse_user(
        self, sync_user
    ):
        user, _ = create_test_user(username="non payload user field")
        sync_user.reset_mock()

        user.is_active = False
        user.save(update_fields=["is_active"])

        sync_user.assert_not_called()

    @patch("home.signals.sync_discourse_user")
    def test_user_save_without_update_fields_syncs_discourse_user(self, sync_user):
        sync_user.return_value = Mock(
            json=Mock(return_value={"success": True}),
            raise_for_status=Mock(),
        )
        user, _ = create_test_user(username="full save user")
        sync_user.reset_mock()

        user.first_name = "Updated"
        user.save()

        sync_user.assert_called_once_with(user)
