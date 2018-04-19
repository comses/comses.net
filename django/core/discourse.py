import os

import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def create_discourse_user(user):
    response = requests.post('{}/users'.format(settings.DISCOURSE_BASE_URL),
                             data=dict(
                                 name=user.get_full_name(),
                                 username=user.username,
                                 email=user.email,
                                 password=''.join(str(c) for c in os.urandom(25)),
                                 active=True,
                             ),
                             params=dict(
                                 api_key=settings.DISCOURSE_API_KEY,
                                 api_username=settings.DISCOURSE_API_USERNAME
                             ))

    return response
