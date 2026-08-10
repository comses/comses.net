import logging
import re
import requests
import shortuuid
import unicodedata
from typing import Optional

from datetime import datetime
from django.contrib.auth import get_user_model
from django.conf import settings

from sqids import Sqids

from core.sso import is_sso_secret_configured, sign_sso_payload

logger = logging.getLogger(__name__)


# Discourse: ASCII_INVALID_CHAR_PATTERN = /[^\w.-]/
# Ruby's \w in a non-Unicode-mode pattern is ASCII-only: [a-zA-Z0-9_]
INVALID_CHARACTERS_PATTERN = re.compile(r"[^\w._-]", re.ASCII)

# Discourse: INVALID_LEADING_CHAR_PATTERN = /\A[^\p{Alnum}\p{M}_]+/
# \p{M} (combining marks) never survives ASCII-folding, so it drops out here
INVALID_LEADING_CHAR_PATTERN = re.compile(r"\A[^a-zA-Z0-9_]+")

# Discourse: INVALID_TRAILING_CHAR_PATTERN = /[^\p{Alnum}\p{M}]+\z/
INVALID_TRAILING_CHAR_PATTERN = re.compile(r"[^a-zA-Z0-9]+\Z")

# Discourse: REPEATED_SPECIAL_CHAR_PATTERN = /[-_.]{2,}/
REPEATED_SPECIAL_CHAR_PATTERN = re.compile(r"[-_.]{2,}")

# Discourse: CONFUSING_EXTENSIONS = /\.(js|json|css|htm|html|xml|jpg|jpeg|png|gif|bmp|ico|tif|tiff|woff)\z/i
INVALID_SUFFIXES_PATTERN = re.compile(
    r"\.(com|net|org|xyz|js|json|css|htm|html|xml|jpg|jpeg|png|gif|bmp|ico|tif|tiff|woff)\Z",
    re.IGNORECASE,
)


DEFAULT_USERNAME_MIN_LENGTH = 3
DEFAULT_USERNAME_MAX_LENGTH = 60


def build_discourse_url(uri):
    return f"{settings.DISCOURSE_BASE_URL}/{uri}"


def get_mock_forum_posts(user=None, number_of_posts=5):
    """
    Returns a canned response for forum activity.
    This is used to mock the response from the Discourse API.
    """
    User = get_user_model()
    if user is None:
        user = User.objects.last()
    member_profile = user.member_profile
    return [
        # adhere to discourse API response structure
        {
            "topic_title": f"Generated Test Forum Post {i}",
            "excerpt": f"Summary of generated test forum post {i}",
            "post_url": f"https://staging-discourse.comses.net/t/topic/{i}",
            "username": get_sanitized_username(member_profile),
            "created_at": datetime.now(),
        }
        for i in range(number_of_posts)
    ]


def get_latest_posts(number_of_posts=5, mock=False):
    if mock:
        return get_mock_forum_posts(number_of_posts=number_of_posts)
    url = build_discourse_url("posts.json")
    logger.debug(
        "fetching posts from %s with deploy environment %s",
        url,
        settings.DEPLOY_ENVIRONMENT,
    )
    response = requests.get(
        url,
        headers={
            "Content-Type": "application/json",
            "Api-Key": settings.DISCOURSE_API_KEY,
            "Api-Username": settings.DISCOURSE_API_USERNAME,
        },
    )
    if response.status_code == 200:
        return response.json()["latest_posts"][:number_of_posts]
    return []


def get_mock_forum_categories(number_of_categories=5):
    # https://docs.discourse.org/#tag/Categories/operation/listCategories
    return {
        "category_list": {
            "can_create_category": False,
            "can_create_topic": False,
            "categories": [
                {
                    "name": f"Test Category {i}",
                    "description": f"Summary of generated test forum category {i}",
                    "slug": f"generated-test-forum-category-{i}",
                    "position": i,
                    "read_restricted": False,
                    "color": f"FF0000",
                }
                for i in range(number_of_categories)
            ],
        }
    }


def get_categories(number_of_categories=5, mock=False):
    if not mock:
        url = build_discourse_url("categories.json?include_subcategories=false")
        response = requests.get(
            url,
            headers={
                "Content-Type": "application/json",
                "Api-Key": settings.DISCOURSE_API_KEY,
                "Api-Username": settings.DISCOURSE_API_USERNAME,
            },
        )
        if response.status_code == 200:
            data = response.json()
        else:
            return []
    else:
        data = get_mock_forum_categories(number_of_categories=number_of_categories)

    categories = data["category_list"]["categories"]
    readable_categories = [
        category for category in categories if category["read_restricted"] == False
    ]
    sorted_categories = sorted(readable_categories, key=lambda x: x["position"])
    return sorted_categories[:number_of_categories]


def get_discourse_sso_user_params(user, avatar_url=None):
    mp = user.member_profile
    params = {
        "external_id": mp.short_uuid,
        "email": user.email,
        "username": get_sanitized_username(mp),
        "require_activation": "false",
        "name": user.get_full_name(),
    }
    if avatar_url:
        params.update(avatar_url=avatar_url)
    return params


def post_discourse_sso_sync(user):
    avatar_url = user.member_profile.avatar_url
    if avatar_url:
        avatar_url = f"{settings.BASE_URL}{avatar_url}"
    payload, signature = sign_sso_payload(
        get_discourse_sso_user_params(user, avatar_url=avatar_url),
        settings.DISCOURSE_SSO_SECRET,
    )
    return requests.post(
        build_discourse_url("admin/users/sync_sso"),
        data={"sso": payload, "sig": signature},
        headers={
            "Api-Key": settings.DISCOURSE_API_KEY,
            "Api-Username": settings.DISCOURSE_API_USERNAME,
        },
    )


def should_sync_discourse_user(user):
    return (
        settings.DEPLOY_ENVIRONMENT.is_staging_or_production
        and is_sso_secret_configured(settings.DISCOURSE_SSO_SECRET)
        and bool(user.email)
    )


def sync_discourse_user(user):
    if not should_sync_discourse_user(user):
        return False

    member_profile = user.member_profile
    if not member_profile.short_uuid:
        member_profile.short_uuid = shortuuid.uuid()
        member_profile.save(update_fields=["short_uuid"])

    try:
        response = post_discourse_sso_sync(user)
        response.raise_for_status()
        _response_data = response.json()
        sso_record = _response_data.get("single_sign_on_record")
        sync_successful = bool(
            _response_data.get("id")
            and sso_record
            and sso_record.get("user_id") == _response_data.get("id")
            and sso_record.get("external_id") == member_profile.short_uuid
        )
        if sync_successful:
            logger.debug(
                "Successfully synced user %s with discourse: %s", user, sso_record
            )
            return True
        else:
            logger.error(
                "Unsuccessful sync for user %s with discourse: %s", user, _response_data
            )

    except (requests.RequestException, ValueError):
        logger.exception("Failed sync request for user %s", user)

    return False


def get_sanitized_username(member_profile):
    return sanitize_username(username=member_profile.username, seed=member_profile.pk)


def discourse_username_suffix(seed: int, min_length=DEFAULT_USERNAME_MIN_LENGTH) -> str:
    return Sqids(min_length=min_length).encode([seed]).casefold()


def sanitize_username(
    username: str,
    min_length: int = DEFAULT_USERNAME_MIN_LENGTH,
    max_length: int = DEFAULT_USERNAME_MAX_LENGTH,
    seed: int = 0,
) -> str:
    """
    Best-effort Discourse username normalizer.

    Handles character-class cleanup, collapsing separators, edge trimming,
    and confusing extensions. Does not guarantee uniqueness or minimum length.
    """
    s = (
        unicodedata.normalize("NFKD", username)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    s = s.casefold()
    s = INVALID_CHARACTERS_PATTERN.sub("-", s)
    s = REPEATED_SPECIAL_CHAR_PATTERN.sub("-", s)
    s = INVALID_LEADING_CHAR_PATTERN.sub("", s)
    s = INVALID_TRAILING_CHAR_PATTERN.sub("", s)
    s = s[:max_length].rstrip("._-")

    while INVALID_SUFFIXES_PATTERN.search(s):
        s = INVALID_SUFFIXES_PATTERN.sub("", s).rstrip("._-")

    if len(s) < min_length:
        base = s[: max_length - 9].rstrip("._-")
        suffix = discourse_username_suffix(seed, min_length=min_length)
        base = s[: max_length - len(suffix) - 1].rstrip("._-")
        s = f"{base}-{suffix}" if base else suffix

    return s or "user"
