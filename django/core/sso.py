import base64
import binascii
import hashlib
import hmac
from urllib import parse

from django.core.cache import cache
from django.core.exceptions import SuspiciousOperation

INVALID_SSO_PAYLOAD = "Invalid payload. Please contact us if this problem persists."
SSO_NONCE_TTL_SECONDS = 10 * 60


def is_sso_secret_configured(secret):
    return bool(secret) and secret != "unconfigured"


class SsoVerificationError(SuspiciousOperation):
    """Raised when an SSO handshake fails protocol verification."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


def sign_sso_payload(params: dict, secret: str) -> tuple[bytes, str]:
    payload = base64.encodebytes(bytes(parse.urlencode(params), "utf-8"))
    signature = hmac.new(
        secret.encode("utf-8"), payload, digestmod=hashlib.sha256
    ).hexdigest()
    return payload, signature


def verify_sso_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected_signature = hmac.new(
        secret.encode("utf-8"), payload, digestmod=hashlib.sha256
    ).hexdigest()
    try:
        signature_bytes = signature.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return hmac.compare_digest(expected_signature.encode("utf-8"), signature_bytes)


def decode_sso_payload(payload: bytes):
    try:
        decoded = base64.decodebytes(payload).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None
    qs = parse.parse_qs(decoded)
    if "nonce" not in qs:
        return None
    return qs


def check_and_consume_sso_nonce(nonce: str, namespace: str) -> bool:
    digest = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
    # Ten minutes covers normal login round trips while bounding cache growth and
    # replay windows.
    return cache.add(
        f"sso:{namespace}:consumed_nonce:{digest}", True, SSO_NONCE_TTL_SECONDS
    )


def build_signed_sso_redirect(
    base_url: str, path: str, params: dict, secret: str
) -> str:
    return_payload, signature = sign_sso_payload(params, secret)
    query_string = parse.urlencode({"sso": return_payload, "sig": signature})
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}?{query_string}"


def get_verified_sso_payload(request, secret: str):
    # Reject duplicate sso or sig parameters to prevent parameter smuggling.
    if len(request.GET.getlist("sso")) > 1 or len(request.GET.getlist("sig")) > 1:
        raise SsoVerificationError(
            "Duplicate SSO parameters detected. Please contact us if this problem persists."
        )

    payload = request.GET.get("sso")
    signature = request.GET.get("sig")

    if not payload or not signature:
        raise SsoVerificationError(
            "No SSO payload or signature. Please contact us if this problem persists."
        )

    payload = bytes(parse.unquote(payload), encoding="utf-8")
    if not verify_sso_signature(payload, signature, secret):
        raise SsoVerificationError(INVALID_SSO_PAYLOAD)

    qs = decode_sso_payload(payload)
    if qs is None:
        raise SsoVerificationError(INVALID_SSO_PAYLOAD)

    return qs
