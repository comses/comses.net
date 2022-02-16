import glob
import logging
import os
import pathlib

from django.conf import settings
from invoke import task

from core.utils import confirm
from .utils import dj

_DEFAULT_DATABASE = "default"

logger = logging.getLogger(__name__)


def get_database_settings(db_key):
    return dict(
        db_name=settings.DATABASES[db_key]["NAME"],
        db_host=settings.DATABASES[db_key]["HOST"],
        db_user=settings.DATABASES[db_key]["USER"],
        db_password=settings.DATABASES[db_key]["PASSWORD"],
    )


@task(aliases=["sh"])
def shell(ctx, db_key=_DEFAULT_DATABASE):
    """Open a pgcli shell to the database"""
    create_pgpass_file(ctx)
    ctx.run(
        "pgcli -h {db_host} -d {db_name} -U {db_user}".format(
            **get_database_settings(db_key)
        ),
        pty=True,
    )


@task(aliases=["pgpass"])
def create_pgpass_file(ctx, db_key=_DEFAULT_DATABASE, force=False):
    db_config = get_database_settings(db_key)
    pgpass_path = os.path.join(os.path.expanduser("~"), ".pgpass")
    if os.path.isfile(pgpass_path) and not force:
        return
    with open(pgpass_path, "w+") as pgpass:
        pgpass.write("db:*:*:{db_user}:{db_password}\n".format(**db_config))
        ctx.run("chmod 0600 ~/.pgpass")


@task(aliases=["b"])
def backup(ctx):
    create_pgpass_file(ctx)
    ctx.run("autopostgresqlbackup")


@task(aliases=["r"])
def reset(ctx):
    drop(ctx, create=True)
    run_migrations(ctx, False)


@task(aliases=["init"])
def run_migrations(ctx, clean=False, initial=False):
    apps = ("core", "home", "library", "curator")
    if clean:
        for app in apps:
            migration_dir = os.path.join(app, "migrations")
            ctx.run("find {0} -name 00*.py -delete -print".format(migration_dir))
    dj(ctx, "makemigrations {0} --noinput".format(" ".join(apps)))
    migrate_command = "migrate --noinput"
    if initial:
        migrate_command += " --fake-initial"
    dj(ctx, migrate_command)


@task(aliases=["d"])
def drop(ctx, database=_DEFAULT_DATABASE, create=False):
    db_config = get_database_settings(database)
    create_pgpass_file(ctx)
    set_connection_limit = (
        'psql -h {db_host} -c "ALTER DATABASE {db_name} connection limit 1;" '
        "-w {db_name} {db_user}"
    ).format(**db_config)
    terminate_backend = (
        "psql -h {db_host} -c "
        '"SELECT pg_terminate_backend(pid) '
        "FROM pg_stat_activity WHERE pid <> pg_backend_pid() AND datname='{db_name}'\" "
        "-w {db_name} {db_user}"
    ).format(**db_config)
    dropdb = "dropdb -w --if-exists -e {db_name} -U {db_user} -h {db_host}".format(
        **db_config
    )
    check_if_database_exists = "psql template1 -tA -U {db_user} -h {db_host} -c \"select 1 from pg_database where datname='{db_name}'\"".format(
        **db_config
    )
    if ctx.run(check_if_database_exists, echo=True).stdout.strip():
        ctx.run(set_connection_limit, echo=True, warn=True)
        ctx.run(terminate_backend, echo=True, warn=True)
        ctx.run(dropdb, echo=True)

    if create:
        ctx.run(
            "createdb -w {db_name} -U {db_user} -h {db_host}".format(**db_config),
            echo=True,
        )


@task(aliases=["rfd"])
def restore_from_dump(
    ctx,
    target_database=_DEFAULT_DATABASE,
    dumpfile=None,
    force=False,
    migrate=True,
    clean_migration=False,
):
    db_config = get_database_settings(target_database)
    if dumpfile is None:
        # XXX: core assumption about how autopostgresqlbackup names new dumps
        dumpfile = glob.glob("/shared/backups/latest/comsesnet_*.sql.gz")[0]
        logger.debug("Using latest autopostgresqlbackup dump %s", dumpfile)

    dumpfile_path = pathlib.Path(dumpfile)
    if dumpfile_path.is_file():
        if not force:
            confirm(
                "This will destroy the database and reload it from {0}. Continue? (y/n) ".format(
                    dumpfile
                )
            )
        cat_cmd = "cat"
        if dumpfile.endswith(".sql.gz"):
            cat_cmd = "zcat"
        drop(ctx, database=target_database, create=True)
        ctx.run(
            "{cat_cmd} {dumpfile} | psql -w -q -o restore-from-dump-log.txt -h db {db_name} {db_user}".format(
                cat_cmd=cat_cmd, dumpfile=dumpfile, **db_config
            ),
            echo=True,
        )
        if migrate:
            run_migrations(ctx, clean=clean_migration, initial=True)
    else:
        logger.warning("Unable to restore from dumpfile %s", dumpfile)
