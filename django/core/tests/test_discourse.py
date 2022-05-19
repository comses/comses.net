from django.test import TestCase

from core.discourse import sanitize_username

import logging

logger = logging.getLogger(__name__)


class DiscourseTestCase(TestCase):

    VALID_USERNAMES = [
        "ab-cd.123_ABC-xYz",
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
