import pathlib
import shlex
import subprocess
import tempfile

import os
from django.core.management.base import BaseCommand

import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Dump DB and filesystem data to archive"

    def add_arguments(self, parser):
        parser.add_argument('--dest', '-d',
                            help='Backup DB and files to folder',
                            default='/shared/backups')

    def handle(self, *args, **options):
        database_config = settings.DATABASES['default']
        logger.info('Backing up database')

        backups = pathlib.Path(options['dest']).joinpath('latest')
        comsesnet_pg_backup = list(backups.glob('{}*'.format(database_config['NAME'])))[0]
        globals_pg_backup = list(backups.glob('postgres_globals*'))[0]
        print('Backing up {} and {}\n'.format(comsesnet_pg_backup, globals_pg_backup))

        subprocess.run(
            shlex.split('borg create --progress --compression lz4 {backup_repo}::{archive_name} {library_path} '
                        '{media_path} {comsesnet_pg_backup} {globals_pg_backup}'.format(
                backup_repo=settings.BACKUP_ROOT,
                archive_name='{now}',
                library_path=settings.LIBRARY_ROOT,
                media_path=settings.MEDIA_ROOT,
                comsesnet_pg_backup=str(comsesnet_pg_backup),
                globals_pg_backup=str(globals_pg_backup))),
            stdout=subprocess.PIPE)
