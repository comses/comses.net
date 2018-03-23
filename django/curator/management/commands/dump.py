import pathlib
import shlex
import subprocess
import tempfile

import os
from django.core.management.base import BaseCommand

import logging
from django.conf import settings

from curator.backup import create_borg_archive

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Dump DB and filesystem data to archive"

    def add_arguments(self, parser):
        parser.add_argument('--dest', '-d',
                            help='Backup DB and files to folder',
                            default=settings.BACKUP_ROOT)
        parser.add_argument('--backup-paths', '-b',
                            help='Comma separated list of backup sql files',
                            default=None)

    def handle(self, *args, **options):
        database_config = settings.DATABASES['default']
        backup_paths = options['backup_paths']
        backups = pathlib.Path(options['dest']).joinpath('latest')
        logger.info('Backing up database')

        if backup_paths is None:
            comsesnet_pg_backup = list(backups.glob('{}*'.format(database_config['NAME'])))[0]
            globals_pg_backup = list(backups.glob('postgres_globals*'))[0]
            print('Backing up {} and {}\n'.format(comsesnet_pg_backup, globals_pg_backup))
            backup_paths = '"{}" "{}"'.format(comsesnet_pg_backup, globals_pg_backup)
        else:
            backup_paths = ' '.join('"{}"'.format(p) for p in backup_paths.split(','))

        create_borg_archive(backup_paths)
