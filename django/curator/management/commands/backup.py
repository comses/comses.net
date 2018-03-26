import pathlib
from django.core.management.base import BaseCommand

import logging
from django.conf import settings
from invoke import Context

from curator.invoke_tasks.borg import backup

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Dump DB and filesystem data to archive"

    def handle(self, *args, **options):
        ctx = Context()
        backup(ctx)
