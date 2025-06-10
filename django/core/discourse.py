import logging
import re
import requests
import shortuuid

from datetime import datetime
from django.contrib.auth import get_user_model
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
            "username": member_profile.discourse_username,
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
