import os

import shutil
import logging
import pathlib
import tempfile
from distutils.util import strtobool
from django.conf import settings
from invoke import task, Collection, Executor, Context, run

logger = logging.getLogger(__name__)

_DEFAULT_DATABASE = 'default'

env = {
    'python': 'python3',
    'project_name': 'cms',
    'project_conf': os.environ.get('DJANGO_SETTINGS_MODULE'),
    'coverage_omit_patterns': ('test', 'settings', 'migrations', 'wsgi', 'management', 'tasks', 'apps.py'),
    'coverage_src_patterns': ('home', 'library', 'core',),
}


def dj(ctx, command, **kwargs):
    """
    Run a Django manage.py command on the server.
    """
    ctx.run('{python} manage.py {dj_command} --settings {project_conf}'.format(dj_command=command, **env),
            **kwargs)


@task(aliases=['init'])
def initialize_repo(ctx):
    if not os.path.exists(settings.BORG_ROOT):
        ctx.run('borg init --encryption=none {}'.format(settings.BORG_ROOT), echo=True)


@task
def backup_database(ctx):
    create_pgpass_file(ctx)
    ctx.run('autopostgresqlbackup')


@task
def backup(ctx):
    create_pgpass_file(ctx)
    dj(ctx, 'dump')


@task(aliases=['pgpass'])
def create_pgpass_file(ctx, db_key=_DEFAULT_DATABASE, force=False):
    db_config = get_database_settings(db_key)
    pgpass_path = os.path.join(os.path.expanduser('~'), '.pgpass')
    if os.path.isfile(pgpass_path) and not force:
        return
    with open(pgpass_path, 'w+') as pgpass:
        pgpass.write('db:*:*:{db_user}:{db_password}\n'.format(**db_config))
        ctx.run('chmod 0600 ~/.pgpass')


def get_database_settings(db_key):
    return dict(
        db_name=settings.DATABASES[db_key]['NAME'],
        db_host=settings.DATABASES[db_key]['HOST'],
        db_user=settings.DATABASES[db_key]['USER'],
        db_password=settings.DATABASES[db_key]['PASSWORD']
    )


@task(aliases=['idb', 'initdb'])
def run_migrations(ctx, clean=False, initial=False):
    apps = ('core', 'home', 'library', 'curator')
    if clean:
        for app in apps:
            migration_dir = os.path.join(app, 'migrations')
            ctx.run('find {0} -name 00*.py -delete -print'.format(migration_dir))
    dj(ctx, 'makemigrations citation --noinput')
    dj(ctx, 'makemigrations {0} --noinput'.format(' '.join(apps)))
    migrate_command = 'migrate --noinput'
    if initial:
        migrate_command += ' --fake-initial'
    dj(ctx, migrate_command)


@task(aliases=['ddb', 'dropdb'])
def drop_database(ctx, database=_DEFAULT_DATABASE, create=False):
    db_config = get_database_settings(database)
    create_pgpass_file(ctx)
    set_connection_limit = 'psql -h {db_host} -c "alter database {db_name} connection limit 1;" -w {db_name} {db_user}'.format(
        **db_config)
    terminate_backend = 'psql -h {db_host} -c "select pg_terminate_backend(pid) from pg_stat_activity where pid <> pg_backend_pid() and datname=\'{db_name}\'" -w {db_name} {db_user}'.format(
        **db_config)
    dropdb = 'dropdb -w --if-exists -e {db_name} -U {db_user} -h {db_host}'.format(**db_config)
    check_if_database_exists = 'psql template1 -tA -U {db_user} -h {db_host} -c "select 1 from pg_database where datname=\'{db_name}\'"'.format(
        **db_config)
    if ctx.run(check_if_database_exists, echo=True).stdout.strip():
        ctx.run(set_connection_limit, echo=True, warn=True)
        ctx.run(terminate_backend, echo=True, warn=True)
        ctx.run(dropdb, echo=True)

    if create:
        ctx.run('createdb -w {db_name} -U {db_user} -h {db_host}'.format(**db_config), echo=True)


@task(aliases=['rfd'])
def restore_from_dump(ctx, target_database=_DEFAULT_DATABASE, dumpfile='comsesnet.sql', force=False, migrate=True):
    db_config = get_database_settings(target_database)
    dumpfile_path = pathlib.Path(dumpfile)
    if dumpfile.endswith('.sql') and dumpfile_path.is_file():
        if not force:
            confirm("This will destroy the database and try to reload it from a dumpfile {0}. Continue? (y/n) ".format(
                dumpfile))
        drop_database(ctx, database=target_database, create=True)
        ctx.run('psql -w -q -h db {db_name} {db_user} < {dumpfile}'.format(dumpfile=dumpfile, **db_config),
                warn=True)
    elif dumpfile.endswith('.sql.gz') and dumpfile_path.is_file():
        if not force:
            confirm("This will destroy the database and try to reload it from a dumpfile {0}. Continue? (y/n) ".format(
                dumpfile))
        drop_database(ctx, database=target_database, create=True)
        ctx.run('zcat {dumpfile} | psql -w -q -h db {db_name} {db_user}'.format(dumpfile=dumpfile, **db_config),
                warn=True)
    if migrate:
        run_migrations(ctx, clean=True, initial=True)


class ChDir:
    def __init__(self, path):
        self.new_path = path
        self.old_path = os.getcwd()

    def __enter__(self):
        os.chdir(self.new_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.old_path)


@task(iterable=['path'])
def create_archive(ctx, library=None, media=None, database=None, share=settings.SHARE_DIR, repo=None, archive=None):
    if repo is None:
        repo = settings.BORG_ROOT
    if archive is None:
        archive = '{now}'
    if not library:
        library = os.path.relpath(settings.LIBRARY_ROOT, share)
    if not media:
        media = os.path.relpath(settings.MEDIA_ROOT, share)
    if not database:
        database = os.path.relpath(os.path.join(settings.BACKUP_ROOT, 'latest'), share)

    with ChDir(share) as c:

        error_msgs = []
        for p in [library, media, database]:
            if not os.path.exists(p):
                error_msgs.append('Path {} does not exist.'.format(p))
        if error_msgs:
            raise IOError('Create archive failed. {}'.format(' '.join(error_msgs)))

        ctx.run('{} borg create --progress --compression lz4 {repo}::"{archive}" {library} {media} {database}'.format(
            borg_environment_variables(), repo=repo, archive=archive, library=library, media=media, database=database), echo=True)


def rotate_library_and_media_files(src_library, src_media):
    logger.info('rotating library and media files')
    latest_dest_library = os.path.join(settings.PREVIOUS_SHARE_ROOT, src_library)
    latest_dest_media = os.path.join(settings.PREVIOUS_SHARE_ROOT, src_media)

    shutil.rmtree(latest_dest_library, ignore_errors=True)
    shutil.rmtree(latest_dest_media, ignore_errors=True)

    os.makedirs(settings.PREVIOUS_SHARE_ROOT, exist_ok=True)
    if os.path.exists(settings.LIBRARY_ROOT):
        shutil.move(settings.LIBRARY_ROOT, settings.PREVIOUS_SHARE_ROOT)
    if os.path.exists(settings.MEDIA_ROOT):
        shutil.move(settings.MEDIA_ROOT, settings.PREVIOUS_SHARE_ROOT)

    shutil.move(src_library, settings.SHARE_DIR)
    shutil.move(src_media, settings.SHARE_DIR)


def borg_environment_variables():
    return "BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK=yes BORG_RELOCATED_REPO_ACCESS_IS_OK=yes"


def _restore(ctx, repo, archive, working_directory, target_database, progress=True):
    if archive is None:
        archive = ctx.run('{} borg list --first 1 --short {repo}'.format(borg_environment_variables(),
                                                                         repo=settings.BORG_ROOT),
                          hide=True).stdout.strip()
        if not archive:
            raise Exception('no borg archives found')

    dumpfile = str(list(pathlib.Path(os.path.join(settings.BACKUP_ROOT, 'latest'))
                        .glob('comsesnet*'))[0])
    with ChDir(working_directory) as c:
        logger.info('Restore (pwd: %s)', os.getcwd())
        extract_cmd = '{} borg extract{progress}{repo}::"{archive}"'.format(
            borg_environment_variables(), repo=repo, archive=archive, progress=' --progress ' if progress else ' ')
        ctx.run(extract_cmd, echo=True)

        src_library = os.path.basename(settings.LIBRARY_ROOT)
        src_media = os.path.basename(settings.MEDIA_ROOT)
        rotate_library_and_media_files(src_library=src_library, src_media=src_media)

        restore_from_dump(ctx, target_database=target_database, dumpfile=dumpfile, force=True, migrate=False)


@task
def restore(ctx, repo=settings.BORG_ROOT, archive=None, target_database=_DEFAULT_DATABASE):
    with tempfile.TemporaryDirectory(dir=settings.SHARE_DIR) as working_directory:
        _restore(ctx, repo, archive=archive, working_directory=working_directory, target_database=target_database)


def confirm(prompt="Continue? (y/n) ", cancel_message="Aborted."):
    response = input(prompt)
    try:
        response_as_bool = strtobool(response)
    except ValueError:
        logger.info("Invalid response %s. Please confirm with yes (y) or no (n).", response_as_bool)
        confirm(prompt, cancel_message)
    if not response_as_bool:
        raise RuntimeError(cancel_message)


BORG_NAMESPACE = Collection('borg', initialize_repo, backup, create_archive, restore)
