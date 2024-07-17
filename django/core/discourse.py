import logging
import re
import requests
import shortuuid

from django.conf import settings

logger = logging.getLogger(__name__)


INVALID_CHARACTERS_PATTERN = re.compile(r"[^\w._-]")
INVALID_LEADING_CHAR_PATTERN = re.compile(r"^[^\w_]+")
INVALID_TRAILING_CHAR_PATTERN = re.compile(r"(_|[^\w])+$")
REPEATED_SPECIAL_CHAR_PATTERN = re.compile(r"[-_.]{2,}")
INVALID_SUFFIXES_PATTERN = re.compile(
    r"\.(com|net|org|xyz|js|json|css|htm|html|xml|jpg|jpeg|png|gif|bmp|ico|tif|tiff|woff)$"
)


DEFAULT_USERNAME_MAX_LENGTH = 60


def build_discourse_url(uri):
    return f"{settings.DISCOURSE_BASE_URL}/{uri}"


def create_discourse_user(user):
    response = requests.post(
        build_discourse_url("users"),
        data=dict(
            name=user.get_full_name(),
            username=user.member_profile.discourse_username,
            email=user.email,
            password=shortuuid.uuid(),
            active=True,
        ),
        headers={
            "Content-Type": "multipart/form-data;",
            "Api-Key": settings.DISCOURSE_API_KEY,
            "Api-Username": settings.DISCOURSE_API_USERNAME,
        },
    )
    return response


def sanitize_username(username, uid=None):
    # defaults: 3 <= username length <= 150
    if uid is None:
        uid = shortuuid.uuid()
    unique_id = uid[:6]
    sanitized_username = INVALID_CHARACTERS_PATTERN.sub(lambda x: "_", username)
    logger.debug("no invalid characters username: %s", sanitized_username)
    sanitized_username = REPEATED_SPECIAL_CHAR_PATTERN.sub(
        lambda x: "_", sanitized_username
    )
    logger.debug("repeated special chars replaced: %s", sanitized_username)
    sanitized_username = INVALID_LEADING_CHAR_PATTERN.sub(
        lambda x: f"_{unique_id}_", sanitized_username
    )
    logger.debug("invalid leading chars replaced: %s", sanitized_username)
    sanitized_username = INVALID_TRAILING_CHAR_PATTERN.sub(
        lambda x: f"_{unique_id}", sanitized_username
    )
    logger.debug("invalid trailing chars replaced: %s", sanitized_username)
    sanitized_username = INVALID_SUFFIXES_PATTERN.sub(
        lambda x: f"_{unique_id}", sanitized_username
    )
    logger.debug("invalid suffixes replaced: %s", sanitized_username)
    return sanitized_username[:DEFAULT_USERNAME_MAX_LENGTH]
