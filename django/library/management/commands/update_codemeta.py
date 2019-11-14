"""
Initializes CoMSES virtual conference Page Models and other canned data.
"""

import logging

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from library.models import CodebaseRelease


logger = logging.getLogger(__name__)

class Command(BaseCommand):

    """
    Updates all codemeta files for all Codebases
    """
    def handle(self, *args, **options):
        for release in CodebaseRelease.objects.all():
            release.get_fs_api().add_codemeta()
