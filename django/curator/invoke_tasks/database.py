import gzip
import logging
import os
import pathlib
import re
from datetime import datetime

from core.utils import confirm
from django.conf import settings
from invoke import task

from .utils import dj

_DEFAULT_DATABASE = "default"
_CREATE_DATABASE_RE = re.compile(r'^CREATE DATABASE (?:(?:"((?:[^"]|"")*)")|([^\s;]+))(?:\s|;)', re.MULTILINE)

logger = logging.getLogger(__name__)


def _get_migration_timestamp():
    return os.environ.get("DB_MIGRATION_TIMESTAMP", datetime.now().strftime("%Y%m%d_%H%M%S"))


def _get_migration_artifact_dir(timestamp=None):
    timestamp = timestamp or _get_migration_timestamp()
    if not timestamp:
        return None
    return pathlib.Path("/migration-artifacts") / timestamp


def _get_migration_dumpfile(db_name, timestamp=None):
    if timestamp is None:
        timestamp = _get_migration_timestamp()
    artifact_dir = _get_migration_artifact_dir(timestamp=timestamp)
    if artifact_dir is None:
        return None
    return artifact_dir / f"{db_name}.dump"


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
        "pgcli -h {db_host} -d {db_name} -U {db_user}".format(**get_database_settings(db_key)),
        pty=True,
    )


@task(aliases=["pgpass"])
def create_pgpass_file(ctx, db_key=_DEFAULT_DATABASE, force=False):
    db_config = get_database_settings(db_key)
    pgpass_path = os.path.join(os.path.expanduser("~"), ".pgpass")
    if os.path.isfile(pgpass_path) and not force:
        return
    with open(pgpass_path, "w+") as pgpass:
        pgpass.write("{db_host}:*:*:{db_user}:{db_password}\n".format(**db_config))
        ctx.run("chmod 0600 ~/.pgpass")


@task(aliases=["b"])
def backup(ctx, database=_DEFAULT_DATABASE):
    db_config = get_database_settings(database)
    dumpfile = pathlib.Path(settings.BACKUP_ROOT) / "latest" / f"{db_config['db_name']}.dump"
    _dump_database(ctx, database, dumpfile)


def _dump_database(ctx, database, dumpfile):
    db_config = get_database_settings(database)
    create_pgpass_file(ctx, db_key=database)
    dumpfile = pathlib.Path(dumpfile)
    temporary_dumpfile = dumpfile.with_suffix(f"{dumpfile.suffix}.tmp")
    dumpfile.parent.mkdir(parents=True, exist_ok=True)
    ctx.run(
        "pg_dump --format=custom --file={temporary_dumpfile} --host={db_host} --username={db_user} {db_name}".format(
            temporary_dumpfile=temporary_dumpfile, **db_config
        ),
        echo=True,
    )
    ctx.run(f"pg_restore --list {temporary_dumpfile} >/dev/null", echo=True)
    os.replace(temporary_dumpfile, dumpfile)


def _database_created_by_plain_dump(dumpfile):
    """Return the database created by a legacy plain-text dump, if present."""
    opener = gzip.open if dumpfile.suffix == ".gz" else open
    with opener(dumpfile, mode="rt", encoding="utf-8", errors="replace") as stream:
        header = stream.read(64 * 1024)
    match = _CREATE_DATABASE_RE.search(header)
    if match is None:
        return None
    return match.group(1).replace('""', '"') if match.group(1) else match.group(2)


@task(aliases=["dm"])
def dump_migration(ctx, database=_DEFAULT_DATABASE, force=False):
    db_config = get_database_settings(database)

    dumpfile = _get_migration_dumpfile(db_config["db_name"])
    if dumpfile is None:
        raise RuntimeError("DB_MIGRATION_TIMESTAMP must be set for dump_migration")
    if not force:
        confirm(f"This will write a postgres dump to {dumpfile}. Continue? (y/n)")
    _dump_database(ctx, database, dumpfile)


@task(aliases=["r"])
def reset(ctx):
    drop(ctx, create=True)
    run_migrations(ctx)


@task(aliases=["init"])
def run_migrations(ctx, initial=False):
    """Apply migration files committed to the application image."""
    migrate_command = "migrate --noinput"
    if initial:
        migrate_command += " --fake-initial"
    dj(ctx, migrate_command)


@task(name="make-migrations", aliases=["mm"])
def make_migrations(ctx):
    """Generate migration files explicitly during development."""
    apps = ("core", "home", "library", "curator")
    dj(ctx, "makemigrations {0} --noinput".format(" ".join(apps)))


@task(aliases=["d"])
def drop(ctx, database=_DEFAULT_DATABASE, create=False):
    db_config = get_database_settings(database)
    create_pgpass_file(ctx)
    set_connection_limit = (
        'psql -h {db_host} -c "ALTER DATABASE {db_name} connection limit 1;" -w {db_name} {db_user}'
    ).format(**db_config)
    terminate_backend = (
        "psql -h {db_host} -c "
        '"SELECT pg_terminate_backend(pid) '
        "FROM pg_stat_activity WHERE pid <> pg_backend_pid() AND datname='{db_name}'\" "
        "-w {db_name} {db_user}"
    ).format(**db_config)
    dropdb = "dropdb -w --if-exists -e {db_name} -U {db_user} -h {db_host}".format(**db_config)
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
        migration_dumpfile = _get_migration_dumpfile(db_config["db_name"])
        if migration_dumpfile is not None and migration_dumpfile.is_file():
            dumpfile_path = migration_dumpfile
            logger.debug("Using migration artifact dump %s", dumpfile_path)
        else:
            current_dumpfile = pathlib.Path(settings.BACKUP_ROOT) / "latest" / f"{db_config['db_name']}.dump"
            if current_dumpfile.is_file():
                dumpfile_path = current_dumpfile
            else:
                legacy_dumpfiles = sorted(current_dumpfile.parent.glob(f"{db_config['db_name']}*.sql*"))
                if not legacy_dumpfiles:
                    raise FileNotFoundError(f"No database dump found in {current_dumpfile.parent}")
                dumpfile_path = legacy_dumpfiles[-1]
            logger.debug("Using latest database dump %s", dumpfile_path)
    else:
        dumpfile_path = pathlib.Path(dumpfile)

    if not dumpfile_path.is_file():
        raise FileNotFoundError(f"Database dump not found: {dumpfile_path}")

    dumpfile = str(dumpfile_path)
    if not force:
        confirm("This will destroy the database and reload it from {0}. Continue? (y/n) ".format(dumpfile))
    if dumpfile.endswith(".dump"):
        drop(ctx, database=target_database, create=True)
        ctx.run(
            "pg_restore --exit-on-error --no-owner --host={db_host} "
            "--username={db_user} --dbname={db_name} {dumpfile}".format(dumpfile=dumpfile, **db_config),
            echo=True,
        )
    else:
        created_database = _database_created_by_plain_dump(dumpfile_path)
        if created_database is not None and created_database != db_config["db_name"]:
            raise ValueError(f"legacy dump creates database {created_database!r}, not target {db_config['db_name']!r}")
        dump_creates_database = created_database is not None
        drop(ctx, database=target_database, create=not dump_creates_database)
        restore_database = "template1" if dump_creates_database else db_config["db_name"]
        cat_cmd = "zcat" if dumpfile.endswith(".sql.gz") else "cat"
        ctx.run(
            "{cat_cmd} {dumpfile} | psql -w --set=ON_ERROR_STOP=1 -q "
            "-o restore-from-dump-log.txt -h {db_host} {restore_database} "
            "{db_user}".format(
                cat_cmd=cat_cmd,
                dumpfile=dumpfile,
                restore_database=restore_database,
                **db_config,
            ),
            echo=True,
        )
    if migrate:
        if clean_migration:
            raise ValueError("clean_migration is no longer supported; migration files must be committed")
        run_migrations(ctx, initial=True)
