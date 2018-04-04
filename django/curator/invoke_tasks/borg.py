import logging
import os
import pathlib
import shutil
import tempfile

from invoke import task, Collection
from django.conf import settings
from .util import dj, confirm
from . import database as db

logger = logging.getLogger(__name__)


@task(aliases=['init'])
def initialize_repo(ctx):
    if not os.path.exists(settings.BORG_ROOT):
        ctx.run('borg init --encryption=none {}'.format(settings.BORG_ROOT), echo=True)


@task(aliases=['b'])
def backup(ctx):
    share = settings.SHARE_DIR
    repo = settings.BORG_ROOT
    # Borg recognizes {now} as the current timestamp
    #  http://borgbackup.readthedocs.io/en/stable/usage/help.html#borg-help-placeholders
    archive = '{utcnow}'
    library = os.path.relpath(settings.LIBRARY_ROOT, share)
    media = os.path.relpath(settings.MEDIA_ROOT, share)
    database = os.path.relpath(os.path.join(settings.BACKUP_ROOT, 'latest'), share)

    error_msgs = []
    for p in [settings.LIBRARY_ROOT, settings.MEDIA_ROOT, os.path.join(settings.BACKUP_ROOT, 'latest')]:
        if not os.path.exists(p):
            error_msgs.append('Path {} does not exist.'.format(p))
    if error_msgs:
        raise IOError('Create archive failed. {}'.format(' '.join(error_msgs)))

    with ctx.cd(share):
        db.create_pgpass_file(ctx)
        ctx.run('{} borg create --progress --compression lz4 {repo}::"{archive}" {library} {media} {database}'.format(
            environment(), repo=repo, archive=archive, library=library, media=media, database=database), echo=True)


DEFAULT_LIBRARY_BASENAME = os.path.basename(settings.LIBRARY_ROOT)
DEFAULT_MEDIA_BASENAME = os.path.basename(settings.MEDIA_ROOT)


def delete_latest_uncompressed_backup(src_library=DEFAULT_LIBRARY_BASENAME, src_media=DEFAULT_MEDIA_BASENAME):
    latest_dest_library = os.path.join(settings.PREVIOUS_SHARE_ROOT, src_library)
    latest_dest_media = os.path.join(settings.PREVIOUS_SHARE_ROOT, src_media)

    shutil.rmtree(latest_dest_library, ignore_errors=True)
    shutil.rmtree(latest_dest_media, ignore_errors=True)


def rotate_library_and_media_files(working_directory,
                                   src_library=DEFAULT_LIBRARY_BASENAME,
                                   src_media=DEFAULT_MEDIA_BASENAME):
    """Rotate the current library and media files

    Current library and media files are moved to the '.latest' folder in case of problems during the restore process.
    Files in .latest can be deleted after you're confident the restore was successful"""
    logger.info('rotating library and media files')
    delete_latest_uncompressed_backup(src_library=src_library, src_media=src_media)

    os.makedirs(settings.PREVIOUS_SHARE_ROOT, exist_ok=True)
    if os.path.exists(settings.LIBRARY_ROOT):
        shutil.move(settings.LIBRARY_ROOT, settings.PREVIOUS_SHARE_ROOT)
    if os.path.exists(settings.MEDIA_ROOT):
        shutil.move(settings.MEDIA_ROOT, settings.PREVIOUS_SHARE_ROOT)

    shutil.move(os.path.join(working_directory, src_library), settings.SHARE_DIR)
    shutil.move(os.path.join(working_directory, src_media), settings.SHARE_DIR)


def environment():
    return "BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK=yes BORG_RELOCATED_REPO_ACCESS_IS_OK=yes"


def _restore_files(working_directory):
    rotate_library_and_media_files(working_directory)


def _restore_database(ctx, working_directory, target_database):
    dumpfile_dir = pathlib.Path(os.path.join(working_directory, os.path.basename(settings.BACKUP_ROOT), 'latest'))
    if not dumpfile_dir.exists():
        raise IOError('dumpfile_dir {} not found'.format(dumpfile_dir))

    dumpfile = str(list(dumpfile_dir.glob('comsesnet*'))[0])

    db.restore_from_dump(ctx, target_database=target_database, dumpfile=dumpfile, force=True, migrate=False)


def _extract(ctx, repo, archive, paths=None):
    extract_cmd = '{} borg extract {repo}::"{archive}"'.format(
        environment(), repo=repo, archive=archive)
    if paths:
        extract_cmd = '{} {}'.format(extract_cmd, ' '.join('"{}"'.format(p) for p in paths))
    print(extract_cmd)
    ctx.run(extract_cmd, echo=True)


def get_latest_bock_backup_archive_name(ctx):
    # borg 1.0 sorts ascending by default so taking the tail will get the most recent backup
    archive = ctx.run('{} borg list --short {repo} | tail -n 1'.format(environment(),
                                                                       repo=settings.BORG_ROOT),
                      echo=True).stdout.strip()
    if not archive:
        raise Exception('no borg archives found')
    return archive


def _restore(ctx, repo, archive, working_directory, target_database, progress=True):
    # Note that working directory is passed as argument. This makes it simpler to use either
    # a persistent directory (for testing and debugging) or a temporary directory
    if archive is None:
        archive = get_latest_bock_backup_archive_name(ctx)

    with ctx.cd(working_directory):
        delete_latest_uncompressed_backup()
        _extract(ctx, repo=repo, archive=archive)
        _restore_files(working_directory)
        _restore_database(ctx, working_directory=working_directory, target_database=target_database)


@task(aliases=['rf'])
def restore_files(ctx, repo=settings.BORG_ROOT, archive=None):
    confirm("Are you sure you want to restore all file content? (y/n)")
    if archive is None:
        archive = get_latest_bock_backup_archive_name(ctx)

    with tempfile.TemporaryDirectory(dir=settings.SHARE_DIR) as working_directory:
        with ctx.cd(working_directory):
            delete_latest_uncompressed_backup()
            _extract(ctx, repo, archive)
            _restore_files(working_directory)


@task(aliases=['rdb'])
def restore_database(ctx, repo=settings.BORG_ROOT, archive=None, target_database=db._DEFAULT_DATABASE):
    confirm("Are you sure you want to restore the database? (y/n) ")
    if archive is None:
        archive = get_latest_bock_backup_archive_name(ctx)

    with tempfile.TemporaryDirectory(dir=settings.SHARE_DIR) as working_directory:
        with ctx.cd(working_directory):
            _extract(ctx, repo, archive, ['backups'])
            _restore_database(ctx, working_directory=working_directory, target_database=target_database)


@task
def restore(ctx, repo=settings.BORG_ROOT, archive=None, target_database=db._DEFAULT_DATABASE):
    """Restore the library files, media files and database to the state given in the borg repo at path REPO
    using archive ARCHIVE. The target_database argument is for testing so a different database can be used to
    make sure the database is getting restored properly"""
    confirm("Are you sure you want to restore the database and all file content? (y/n)")
    with tempfile.TemporaryDirectory(dir=settings.SHARE_DIR) as working_directory:
        _restore(ctx, repo, archive=archive, working_directory=working_directory, target_database=target_database)
