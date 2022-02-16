import logging
import os

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def build_discourse_url(uri):
    return f"{settings.DISCOURSE_BASE_URL}/{uri}"


def create_discourse_user(user):
    response = requests.post(
        build_discourse_url("users"),
        data=dict(
            name=user.get_full_name(),
            username=user.username,
            email=user.email,
            password="".join(str(c) for c in os.urandom(25)),
            active=True,
        ),
        headers={
            "Content-Type": "multipart/form-data;",
            "Api-Key": settings.DISCOURSE_API_KEY,
            "Api-Username": settings.DISCOURSE_API_USERNAME,
        },
    )
    return response
