import os
import pathlib

from invoke import task
from django.conf import settings
from .util import dj, confirm

_DEFAULT_DATABASE = 'default'


def get_database_settings(db_key):
    return dict(
        db_name=settings.DATABASES[db_key]['NAME'],
        db_host=settings.DATABASES[db_key]['HOST'],
        db_user=settings.DATABASES[db_key]['USER'],
        db_password=settings.DATABASES[db_key]['PASSWORD']
    )


@task(aliases=['sh'])
def shell(ctx, db_key=_DEFAULT_DATABASE):
    """Open a pgcli shell to the database"""
    ctx.run('pgcli -h {db_host} -d {db_name} -U {db_user}'.format(**get_database_settings(db_key)), pty=True)


@task(aliases=['pgpass'])
def create_pgpass_file(ctx, db_key=_DEFAULT_DATABASE, force=False):
    db_config = get_database_settings(db_key)
    pgpass_path = os.path.join(os.path.expanduser('~'), '.pgpass')
    if os.path.isfile(pgpass_path) and not force:
        return
    with open(pgpass_path, 'w+') as pgpass:
        pgpass.write('db:*:*:{db_user}:{db_password}\n'.format(**db_config))
        ctx.run('chmod 0600 ~/.pgpass')


@task(aliases=['b'])
def backup(ctx):
    create_pgpass_file(ctx)
    ctx.run('autopostgresqlbackup')


@task(aliases=['r'])
def reset(ctx):
    drop(ctx, create=True)
    run_migrations(ctx, False)


@task(aliases=['init'])
def run_migrations(ctx, clean=False, initial=False):
    apps = ('core', 'home', 'library', 'curator')
    if clean:
        for app in apps:
            migration_dir = os.path.join(app, 'migrations')
            ctx.run('find {0} -name 00*.py -delete -print'.format(migration_dir))
    # dj(ctx, 'makemigrations citation --noinput')
    dj(ctx, 'makemigrations {0} --noinput'.format(' '.join(apps)))
    migrate_command = 'migrate --noinput'
    if initial:
        migrate_command += ' --fake-initial'
    dj(ctx, migrate_command)


@task(aliases=['d'])
def drop(ctx, database=_DEFAULT_DATABASE, create=False):
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
        drop(ctx, database=target_database, create=True)
        ctx.run('psql -w -q -h db {db_name} {db_user} < {dumpfile}'.format(dumpfile=dumpfile, **db_config), echo=True)
    elif dumpfile.endswith('.sql.gz') and dumpfile_path.is_file():
        if not force:
            confirm("This will destroy the database and try to reload it from a dumpfile {0}. Continue? (y/n) ".format(
                dumpfile))
        drop(ctx, database=target_database, create=True)
        ctx.run('zcat {dumpfile} | psql -w -q -h db {db_name} {db_user}'.format(dumpfile=dumpfile, **db_config), echo=True)
    if migrate:
        run_migrations(ctx, clean=True, initial=True)
