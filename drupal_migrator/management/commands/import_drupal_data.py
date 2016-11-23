"""
Management command for loading JSON dump of old CoMSES.net website into the new site
"""

from django.core.management.base import BaseCommand
from ...database_migration import load

import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--directory', '-d',
                            help='directory to load Drupal 7 data dump from')

    def handle(self, *args, **options):
        directory = options['directory']
        load(directory)
