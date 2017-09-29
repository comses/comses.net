"""
Load openabm.org JSON dumps into the new site
"""

import logging

from django.core.management.base import BaseCommand

from drupal_migrator.database_migration import load

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--directory', '-d',
                            help='Directory with Drupal 7 JSON data dumps to be loaded')

    def handle(self, *args, **options):
        directory = options['directory']
        load(directory)
