import base64
import hashlib
import hmac
import logging
from urllib import parse

from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import ComsesGroups

from .base import create_test_user
from core.discourse import get_sanitized_username

logger = logging.getLogger(__name__)

# the secret and nonce from the worked example in the librarian SSO wire contract; also reused
# as arbitrary-but-fixed values for discourse_sso, which has no comparable published example
TEST_SECRET = "test-secret-do-not-use-in-production"
TEST_NONCE = "0123456789abcdef0123456789abcdef"
TEST_LIBRARIAN_BASE_URL = "https://librarian.example.net"
TEST_DISCOURSE_BASE_URL = "https://discourse.example.net"
TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "sso-tests",
    }
}


def sign(payload: bytes, secret=TEST_SECRET):
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def build_request(nonce=TEST_NONCE, return_to="/", secret=TEST_SECRET):
    """build the ?sso=&sig= pair a provider sends to an sso endpoint"""
    payload = base64.encodebytes(
        parse.urlencode({"nonce": nonce, "return_to": return_to}).encode("utf-8")
    )
    return {"sso": payload.decode("utf-8"), "sig": sign(payload, secret)}


class SsoHandshakeAssertions:
    """
    Shared protocol-level coverage for discourse_sso and librarian_sso.

    Both views are built from the same handshake helpers (verify_sso_signature,
    decode_sso_payload, check_and_consume_sso_nonce, build_signed_sso_redirect), so a bug in
    that shared code would show up identically in both. This mixin runs the shared protocol
    suite once per concrete subclass instead of maintaining two copies that can drift apart.

    Deliberately NOT a TestCase subclass itself, so it is never discovered and run on its own -
    only `class Foo(SsoHandshakeAssertions, TestCase)` is collected. A subclass must set
    `url_name`, implement `create_user()` if it needs anything beyond a bare user, and implement
    `assert_valid_response()` for its own callback URL shape. Anything specific to one provider
    (librarian's group-gating, the worked-example signature pin, discourse's user-field mapping)
    belongs on the subclass, not here.
    """

    url_name = None

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.url = reverse(self.url_name)
        self.user, self.user_factory = self.create_user()

    def create_user(self):
        return create_test_user(username="sso_user")

    def login(self, user=None):
        user = self.user if user is None else user
        self.assertTrue(
            self.client.login(
                username=user.username, password=self.user_factory.password
            )
        )

    def assert_valid_response(self, response, secret=TEST_SECRET):
        """verify the signature on a callback redirect and return (params, signature)"""
        raise NotImplementedError

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.url, build_request())
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_missing_payload_or_signature(self):
        self.login()
        request = build_request()
        for params in ({}, {"sso": request["sso"]}, {"sig": request["sig"]}):
            with self.subTest(params=sorted(params)):
                self.assertEqual(self.client.get(self.url, params).status_code, 400)

    def test_empty_payload(self):
        self.login()
        response = self.client.get(self.url, {"sso": "", "sig": build_request()["sig"]})
        self.assertEqual(response.status_code, 400)

    def test_tampered_signature(self):
        self.login()
        request = build_request()
        request["sig"] = request["sig"][:-1] + (
            "0" if request["sig"][-1] != "0" else "1"
        )
        self.assertEqual(self.client.get(self.url, request).status_code, 400)

    def test_payload_signed_with_the_wrong_secret(self):
        self.login()
        request = build_request(secret="not-the-configured-secret")
        self.assertEqual(self.client.get(self.url, request).status_code, 400)

    def test_tampered_payload(self):
        self.login()
        request = build_request()
        request["sso"] = build_request(nonce="f" * 32)["sso"]
        self.assertEqual(self.client.get(self.url, request).status_code, 400)

    def test_non_ascii_signature(self):
        """hmac.compare_digest raises TypeError when handed a non-ASCII str; both sides must be
        encoded to bytes before comparison rather than compared as str"""
        self.login()
        request = build_request()
        request["sig"] = "ü" * 64
        self.assertEqual(self.client.get(self.url, request).status_code, 400)

    def test_malformed_payload_is_rejected_before_decoding(self):
        """
        each of these is signed with the configured secret so it gets past signature verification
        and reaches the decode, which must return 400 rather than raising a 500
        """
        self.login()
        # b"////" decodes to bytes that are not valid utf-8, b"abcde" is not valid base64
        for payload in (b"////", b"abcde"):
            with self.subTest(payload=payload):
                response = self.client.get(
                    self.url,
                    {"sso": payload.decode("utf-8"), "sig": sign(payload)},
                )
                self.assertEqual(response.status_code, 400)

    def test_payload_without_a_nonce_parameter(self):
        """
        a substring guard on the decoded payload would let foo=nonce through and then raise a
        KeyError on the way out, so the nonce is checked as a parsed parameter
        """
        self.login()
        for value in ("foo=bar", "foo=nonce"):
            with self.subTest(value=value):
                payload = base64.encodebytes(value.encode("utf-8"))
                response = self.client.get(
                    self.url,
                    {"sso": payload.decode("utf-8"), "sig": sign(payload)},
                )
                self.assertEqual(response.status_code, 400)

    def test_replayed_nonce_is_rejected(self):
        self.login()
        request = build_request()
        self.assert_valid_response(self.client.get(self.url, request))
        self.assertEqual(self.client.get(self.url, request).status_code, 400)

    def test_non_get_method_is_rejected(self):
        self.login()
        request = build_request()
        # POST/PUT/DELETE should not be processed as SSO handshakes
        for method in (self.client.post, self.client.put, self.client.delete):
            with self.subTest(method=method.__name__):
                response = method(self.url, request)
                self.assertEqual(response.status_code, 405)

    def test_duplicate_parameters_are_rejected(self):
        self.login()
        request = build_request()

        cases = [
            (
                "duplicate sso",
                f"{self.url}?sso={request['sso']}&sso=tampered&sig={request['sig']}",
            ),
            (
                "duplicate sig",
                f"{self.url}?sso={request['sso']}&sig={request['sig']}&sig=tampered",
            ),
            (
                "both duplicated",
                f"{self.url}?sso={request['sso']}&sso=tampered&sig={request['sig']}&sig=tampered",
            ),
        ]

        for label, url in cases:
            with self.subTest(label=label):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 400)

    def test_malicious_return_to_is_ignored(self):
        """
        The return_to parameter is part of the signed payload, but the view
        should not use it to construct the final redirect (preventing open redirects).
        """
        self.login()
        # Sign a payload that tries to redirect to an external site
        payload_data = {"nonce": TEST_NONCE, "return_to": "https://evil.com"}
        payload = base64.encodebytes(
            parse.urlencode(payload_data).encode("utf-8")
        ).decode("utf-8")
        sig = sign(payload.encode("utf-8"))

        response = self.client.get(self.url, {"sso": payload, "sig": sig})

        # Verify the response is still a valid provider redirect
        params, _ = self.assert_valid_response(response)

        # Verify the outbound payload does NOT contain return_to
        self.assertNotIn("return_to", params)


@override_settings(
    LIBRARIAN_SSO_SECRET=TEST_SECRET,
    LIBRARIAN_BASE_URL=TEST_LIBRARIAN_BASE_URL,
    CACHES=TEST_CACHES,
)
class LibrarianSsoTestCase(SsoHandshakeAssertions, TestCase):
    """
    the secret must be set explicitly on every test class, a deployment that never provisioned it
    reads as "" and an unset secret would make every assertion below pass vacuously
    """

    url_name = "core:librarian-sso"

    def create_user(self):
        user, factory = create_test_user(username="librarian_user")
        ComsesGroups.LIBRARIAN.add(user)
        return user, factory

    def assert_valid_response(self, response, secret=TEST_SECRET):
        self.assertEqual(response.status_code, 302)
        prefix = f"{TEST_LIBRARIAN_BASE_URL}/auth/sso/callback?"
        location = response["Location"]
        self.assertTrue(location.startswith(prefix), location)
        query = parse.parse_qs(location[len(prefix) :])
        payload = query["sso"][0].encode("utf-8")
        signature = query["sig"][0]
        self.assertEqual(signature, sign(payload, secret))
        params = parse.parse_qs(base64.decodebytes(payload).decode("utf-8"))
        return params, signature

    def test_librarian_group_created_by_migration(self):
        self.assertTrue(
            Group.objects.filter(name=ComsesGroups.LIBRARIAN.value).exists()
        )

    def test_valid_handshake(self):
        self.login()
        response = self.client.get(self.url, build_request())
        params, _ = self.assert_valid_response(response)
        self.assertEqual(params["nonce"], [TEST_NONCE])
        # FIXME: librarian SSO uses PK as external id, address for consistency later
        self.assertEqual(params["external_id"], [str(self.user.pk)])
        self.assertEqual(params["email"], [self.user.email])
        self.assertEqual(params["username"], [self.user.username])
        self.assertEqual(params["groups"], [ComsesGroups.LIBRARIAN.value])
        self.assertEqual(params["is_librarian_user"], ["true"])
        # return_to is never echoed back, the Librarian holds it server-side
        self.assertNotIn("return_to", params)

    def test_groups_are_limited_to_comses_groups(self):
        ComsesGroups.initialize()
        ComsesGroups.FULL_MEMBER.add(self.user)
        self.user.groups.add(Group.objects.create(name="Some Other Group"))
        self.login()
        params, _ = self.assert_valid_response(
            self.client.get(self.url, build_request())
        )
        self.assertEqual(params["groups"], ["Full Members,Librarian Users"])

    def test_matches_worked_example_signature(self):
        """
        pins the encoding against the signature published in the wire contract - base64.encodebytes
        embeds newlines every 76 characters and they are inside the signed material, so an
        implementation that strips whitespace before signing produces a different digest here
        """
        ComsesGroups.initialize()
        user = User.objects.create_user(
            id=4242,
            username="someone",
            email="someone@example.edu",
            first_name="Some",
            last_name="One",
            password=self.user_factory.password,
        )
        ComsesGroups.FULL_MEMBER.add(user)
        ComsesGroups.LIBRARIAN.add(user)
        self.login(user)
        _, signature = self.assert_valid_response(
            self.client.get(self.url, build_request())
        )
        self.assertEqual(
            signature,
            "ad7e81e8535e5896dbe4677dfdf668248f02bec2b3b19e9db6540bf993f1475a",
        )

    def test_non_member_gets_an_explanatory_403(self):
        non_member = self.user_factory.create(username="not_a_librarian")
        self.login(non_member)
        response = self.client.get(self.url, build_request())
        self.assertContains(
            response, "CoMSES Librarian access required", status_code=403
        )

    def test_membership_is_reevaluated_on_every_handshake(self):
        """
        membership is read with ComsesGroups.is_member, not get_group, which memoises a Group
        instance on the module level Enum member with no invalidation
        """
        self.login()
        self.assert_valid_response(self.client.get(self.url, build_request()))
        self.user.groups.clear()
        response = self.client.get(self.url, build_request())
        self.assertEqual(response.status_code, 403)


@override_settings(
    LIBRARIAN_SSO_SECRET=TEST_SECRET,
    LIBRARIAN_BASE_URL="",
    CACHES=TEST_CACHES,
)
class LibrarianSsoNotConfiguredTestCase(TestCase):
    """an unset LIBRARIAN_BASE_URL turns the integration off rather than half-on

    Kept separate from the shared mixin rather than generalized: librarian_sso fails closed on
    two independent settings (secret AND base_url), while discourse_sso only checks its secret
    (see DiscourseSsoTestCase.test_empty_or_placeholder_secret_fails_closed) - forcing both into
    one shared "not configured" test would need conditional logic per provider that's harder to
    read than just stating each provider's actual requirement directly.
    """

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user, self.user_factory = create_test_user(
            username="librarian_unconfigured"
        )
        ComsesGroups.LIBRARIAN.add(self.user)
        self.client.force_login(self.user)

    def test_view_is_absent_when_the_secret_is_missing(self):
        """read_secret returns "" for a missing file; signing with an empty key is refused"""
        with self.settings(
            LIBRARIAN_SSO_SECRET="", LIBRARIAN_BASE_URL=TEST_LIBRARIAN_BASE_URL
        ):
            response = self.client.get(reverse("core:librarian-sso"), build_request())
            self.assertEqual(response.status_code, 404)

    def test_view_is_absent_when_the_integration_is_not_configured(self):
        """404 rather than signing claims aimed at a relative URL that 404s anyway

        a member with a valid payload is the ONLY caller that reaches the redirect,
        so this is the case that would otherwise emit the user's email, username
        and groups into a Location header pointing back at this site
        """
        response = self.client.get(reverse("core:librarian-sso"), build_request())
        self.assertEqual(response.status_code, 404)


@override_settings(
    DISCOURSE_SSO_SECRET=TEST_SECRET,
    DISCOURSE_BASE_URL=TEST_DISCOURSE_BASE_URL,
    CACHES=TEST_CACHES,
)
class DiscourseSsoTestCase(SsoHandshakeAssertions, TestCase):
    url_name = "core:discourse-sso"

    def create_user(self):
        return create_test_user(
            username="discourse_user", first_name="Discourse", last_name="User"
        )

    def assert_valid_response(self, response, secret=TEST_SECRET):
        self.assertEqual(response.status_code, 302)
        prefix = f"{TEST_DISCOURSE_BASE_URL}/session/sso_login?"
        location = response["Location"]
        self.assertTrue(location.startswith(prefix), location)
        query = parse.parse_qs(location[len(prefix) :])
        payload = query["sso"][0].encode("utf-8")
        signature = query["sig"][0]
        self.assertEqual(signature, sign(payload, secret))
        params = parse.parse_qs(base64.decodebytes(payload).decode("utf-8"))
        return params, signature

    def test_valid_handshake(self):
        self.login()
        params, _ = self.assert_valid_response(
            self.client.get(self.url, build_request())
        )
        self.assertEqual(params["nonce"], [TEST_NONCE])
        self.assertEqual(
            params["external_id"], [str(self.user.member_profile.short_uuid)]
        )
        self.assertEqual(params["email"], [self.user.email])
        self.assertEqual(
            params["username"], [get_sanitized_username(self.user.member_profile)]
        )
        self.assertEqual(params["require_activation"], ["false"])
        self.assertEqual(params["name"], [self.user.get_full_name()])

    def test_empty_or_placeholder_secret_fails_closed(self):
        self.login()
        with self.settings(DISCOURSE_SSO_SECRET=""):
            response = self.client.get(self.url, build_request())
            self.assertEqual(response.status_code, 404)
