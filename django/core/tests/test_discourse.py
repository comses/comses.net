import base64
from urllib import parse

from django.test import TestCase, override_settings

from core.discourse import (
    get_discourse_sso_user_params,
    get_sanitized_username,
    sanitize_username,
)
from core.sso import sign_sso_payload
from core.tests.base import create_test_user

import logging

logger = logging.getLogger(__name__)


class DiscourseTestCase(TestCase):
    VALID_USERNAMES = [
        "ab-cd.123_abc-xyz",
        "xyzzy",
        "xyzzyabcd9",
        "_abc",
    ]

    INVALID_USERNAMES = [
        "abc|",
        "a#bc",
        "abc xyz",
        ".abc",
        "-abc",
        "abc_",
        "abc.",
        "abc-",
        "ab__cd",
        "ab..cd",
        "ab--cd",
        # emails
        "abc@mailinator.com",
        "abc@exchange.edu",
        "abc@asu.edu",
        "abc@gmail.com",
        # invalid suffix
        "abc.jpeg",
        "abc.json",
        "abc.gif",
    ]

    def test_sanitize_username(self):
        for username in self.VALID_USERNAMES:
            logger.debug("comparing %s <-> %s", username, sanitize_username(username))
            self.assertEqual(username, sanitize_username(username))

        for username in self.INVALID_USERNAMES:
            logger.debug("comparing %s <-> %s", username, sanitize_username(username))
            self.assertNotEqual(username, sanitize_username(username))


@override_settings(BASE_URL="https://www.example.net", DISCOURSE_SSO_SECRET="secret")
class DiscourseConnectSyncTestCase(TestCase):
    def test_sync_sso_payload_uses_discourse_identity(self):
        user, _ = create_test_user(
            username="discourse user", first_name="Discourse", last_name="User"
        )
        mp = user.member_profile

        params = get_discourse_sso_user_params(user)
        self.assertEqual(params["external_id"], mp.short_uuid)
        self.assertEqual(params["email"], user.email)
        self.assertEqual(params["username"], get_sanitized_username(mp))
        self.assertEqual(params["require_activation"], "false")
        self.assertEqual(params["name"], user.get_full_name())

        payload, signature = sign_sso_payload(params, "secret")
        decoded_params = parse.parse_qs(base64.decodebytes(payload).decode("utf-8"))
        self.assertEqual(decoded_params["external_id"], [str(mp.short_uuid)])
        self.assertEqual(decoded_params["email"], [user.email])
        self.assertEqual(decoded_params["username"], [get_sanitized_username(mp)])
        self.assertTrue(signature)

    def test_sync_sso_params_preserve_absolute_avatar_url(self):
        user, _ = create_test_user(username="avatar user")
        params = get_discourse_sso_user_params(
            user, avatar_url="https://www.example.net/avatar.png"
        )

        self.assertEqual(params["avatar_url"], "https://www.example.net/avatar.png")
