"""
Management command for loading JSON dump of old CoMSES.net website into the new site
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from drupal_migrator.file_migration import load

import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--directory', '-d',
                            help='source directory with openabm.org Drupal 7 `models` folder')

    def handle(self, *args, **options):
        directory = options['directory']
        load(directory)
