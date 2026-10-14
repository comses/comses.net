from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
from pathlib import Path
import shutil
import tempfile

from django.conf import settings
from invoke import task

from . import database as db
from core.utils import confirm

DEFAULT_LIBRARY_BASENAME = Path(settings.LIBRARY_ROOT).name
DEFAULT_MEDIA_BASENAME = Path(settings.MEDIA_ROOT).name
DEFAULT_REPOSITORY_BASENAME = Path(settings.REPOSITORY_ROOT).name
MAX_PRUNE_BACKUP_AGE_SECONDS = 2 * 24 * 60 * 60


@task(aliases=["init"])
def initialize_repo(ctx):
    if not Path(settings.BORG_ROOT).exists():
        ctx.run(f"borg init --encryption=none {settings.BORG_ROOT}", echo=True)


@task(aliases=["list", "l"])
def borg_list(ctx):
    ctx.run(f"borg list {settings.BORG_ROOT}", echo=True, env=environment())


def _prune(ctx):
    # FIXME: provide cli override of these defaults
    daily = 14
    weekly = 4
    monthly = 12
    yearly = -1
    ctx.run(
        f"borg prune --verbose --list --keep-daily {daily} --keep-weekly {weekly} --keep-monthly {monthly} --keep-yearly {yearly} {settings.BORG_ROOT}",
        echo=True,
        env=environment(),
    )
    ctx.run(f"borg compact --verbose {settings.BORG_ROOT}")


@task(name="prune", aliases=["p"])
def borg_prune(ctx):
    success_path = Path(settings.BACKUP_ROOT) / "last-successful-backup"
    if not success_path.is_file():
        raise RuntimeError("refusing to prune without a successful backup marker")
    marker_age = datetime.now(timezone.utc).timestamp() - success_path.stat().st_mtime
    if marker_age > MAX_PRUNE_BACKUP_AGE_SECONDS:
        raise RuntimeError("refusing to prune: last successful backup is too old")

    with exclusive_backup_operation("prune"):
        _prune(ctx)


@task(aliases=["b"])
def backup(ctx):
    share = settings.SHARE_DIR
    repo = settings.BORG_ROOT
    archive = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    share_path = Path(share)
    library_root = Path(settings.LIBRARY_ROOT)
    media_root = Path(settings.MEDIA_ROOT)
    repository_root = Path(settings.REPOSITORY_ROOT)
    backup_latest_root = Path(settings.BACKUP_ROOT) / "latest"

    library = library_root.relative_to(share_path)
    media = media_root.relative_to(share_path)
    repository = repository_root.relative_to(share_path)
    database = backup_latest_root.relative_to(share_path)

    error_msgs = []
    for p in (library_root, media_root, repository_root, backup_latest_root):
        if not p.exists():
            error_msgs.append(f"Path {p} does not exist.")
    if error_msgs:
        raise IOError("Create archive failed. {}".format(" ".join(error_msgs)))

    with ctx.cd(share):
        ctx.run(
            f'borg create --stats --compression lz4 {repo}::"{archive}" {library} {media} {repository} {database}',
            echo=True,
            env=environment(),
        )
    check_archive(ctx, repo, archive)
    return archive


def check_archive(ctx, repo, archive):
    ctx.run(
        f'borg check --verify-data {repo}::"{archive}"',
        echo=True,
        env=environment(),
    )


@task(name="backup-all")
def backup_all(ctx):
    """Create and verify one database and filesystem backup under a shared lock."""
    backup_root = Path(settings.BACKUP_ROOT)
    success_path = backup_root / "last-successful-backup"

    with exclusive_backup_operation("backup"):
        db.backup(ctx)
        archive = backup(ctx)
        timestamp = datetime.now(timezone.utc).isoformat()
        temporary_success_path = success_path.with_suffix(".tmp")
        temporary_success_path.write_text(f"timestamp={timestamp}\narchive={archive}\n", encoding="ascii")
        temporary_success_path.replace(success_path)


@contextmanager
def exclusive_backup_operation(operation):
    backup_root = Path(settings.BACKUP_ROOT)
    backup_root.mkdir(parents=True, exist_ok=True)
    lock_path = backup_root / ".backup.lock"
    with lock_path.open("a+") as lockfile:
        try:
            fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"another backup operation is running; cannot start {operation}") from exc
        yield


def delete_latest_uncompressed_backup(
    src_library=DEFAULT_LIBRARY_BASENAME,
    src_media=DEFAULT_MEDIA_BASENAME,
    src_repository=DEFAULT_REPOSITORY_BASENAME,
):
    previous = Path(settings.PREVIOUS_SHARE_ROOT)
    latest_dest_library = previous / src_library
    latest_dest_media = previous / src_media
    latest_dest_repository = previous / src_repository

    shutil.rmtree(latest_dest_library, ignore_errors=True)
    shutil.rmtree(latest_dest_media, ignore_errors=True)
    shutil.rmtree(latest_dest_repository, ignore_errors=True)


def rotate_library_and_media_files(
    working_directory,
    src_library=DEFAULT_LIBRARY_BASENAME,
    src_media=DEFAULT_MEDIA_BASENAME,
    src_repository=DEFAULT_REPOSITORY_BASENAME,
):
    """
    Rotate the current library, media, and repository files

    Current library, media, and repository files are moved to the '.latest' folder in case of problems during the restore process.
    Files in .latest can be deleted if the restore was successful
    """
    print("rotating library, media, and repository files")
    delete_latest_uncompressed_backup(src_library=src_library, src_media=src_media, src_repository=src_repository)

    previous = Path(settings.PREVIOUS_SHARE_ROOT)
    share_root = Path(settings.SHARE_DIR)
    library_root = Path(settings.LIBRARY_ROOT)
    media_root = Path(settings.MEDIA_ROOT)
    repository_root = Path(settings.REPOSITORY_ROOT)
    working_root = Path(working_directory)

    previous.mkdir(exist_ok=True)
    if library_root.exists():
        shutil.move(library_root, previous)
    if media_root.exists():
        shutil.move(media_root, previous)
    if repository_root.exists():
        shutil.move(repository_root, previous)

    shutil.move(working_root / src_library, share_root)
    shutil.move(working_root / src_media, share_root)
    # repository dir may not exist in older backups
    src_repository_path = working_root / src_repository
    if src_repository_path.exists():
        shutil.move(src_repository_path, share_root)


def environment():
    return {
        "BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK": "yes",
        "BORG_RELOCATED_REPO_ACCESS_IS_OK": "yes",
    }


def _restore_files(working_directory):
    rotate_library_and_media_files(working_directory)


def _restore_database(ctx, working_directory, target_database):
    backup_root_name = Path(settings.BACKUP_ROOT).name
    dumpfile_dir = Path(working_directory) / backup_root_name / "latest"
    if not dumpfile_dir.exists():
        raise IOError("dumpfile_dir {} not found".format(dumpfile_dir))
    database_name = settings.DATABASES[db._DEFAULT_DATABASE]["NAME"]
    dumpfile_path = dumpfile_dir / f"{database_name}.dump"
    if not dumpfile_path.exists():
        legacy_dumpfiles = sorted(dumpfile_dir.glob(f"{database_name}*.sql*"))
        if not legacy_dumpfiles:
            raise FileNotFoundError(f"No database dump found in {dumpfile_dir}")
        dumpfile_path = legacy_dumpfiles[-1]
    db.restore_from_dump(
        ctx,
        target_database=target_database,
        dumpfile=str(dumpfile_path),
        force=True,
        migrate=False,
    )


def _extract(ctx, repo, archive, paths=None):
    extract_cmd = 'borg extract {repo}::"{archive}"'.format(repo=repo, archive=archive)
    if paths:
        extract_cmd = "{} {}".format(extract_cmd, " ".join('"{}"'.format(p) for p in paths))
    print(extract_cmd)
    ctx.run(extract_cmd, env=environment(), echo=True)


@task(aliases=["lb"])
def get_latest_borg_backup_archive_name(ctx, repo):
    # borg 1.0 sorts ascending by default so taking the tail will get the most recent backup
    archive = ctx.run(
        "borg list --short {repo} | tail -n 1".format(repo=repo),
        echo=True,
        env=environment(),
    ).stdout.strip()
    if not archive:
        raise RuntimeError("no borg archives found")
    return archive


def _restore(ctx, repo, archive, working_directory, target_database):
    # Note that working directory is passed as argument. This makes it simpler to use either
    # a persistent directory (for testing and debugging) or a temporary directory
    with exclusive_backup_operation("restore"):
        if archive is None:
            archive = get_latest_borg_backup_archive_name(ctx, repo=repo)

        check_archive(ctx, repo, archive)
        with ctx.cd(working_directory):
            _extract(ctx, repo=repo, archive=archive)
            _restore_database(
                ctx,
                working_directory=working_directory,
                target_database=target_database,
            )
            ctx.run("/code/manage.py migrate")
            _restore_files(working_directory)


@task(aliases=["rf"])
def restore_files(ctx, repo=settings.BORG_ROOT, archive=None):
    confirm("Are you sure you want to restore all file content (y/n)? ")
    with exclusive_backup_operation("restore"):
        if archive is None:
            archive = get_latest_borg_backup_archive_name(ctx, repo=repo)

        check_archive(ctx, repo, archive)
        with tempfile.TemporaryDirectory(dir=settings.SHARE_DIR) as working_directory:
            with ctx.cd(working_directory):
                _extract(ctx, repo, archive)
                _restore_files(working_directory)


@task(aliases=["rdb"])
def restore_database(ctx, repo=settings.BORG_ROOT, archive=None, target_database=db._DEFAULT_DATABASE):
    confirm("Are you sure you want to restore the database (y/n)? ")
    with exclusive_backup_operation("restore"):
        if archive is None:
            archive = get_latest_borg_backup_archive_name(ctx, repo=repo)

        check_archive(ctx, repo, archive)
        with tempfile.TemporaryDirectory(dir=settings.SHARE_DIR) as working_directory:
            with ctx.cd(working_directory):
                _extract(ctx, repo, archive, ["backups"])
                _restore_database(
                    ctx,
                    working_directory=working_directory,
                    target_database=target_database,
                )
                ctx.run("/code/manage.py migrate")


@task()
def restore(
    ctx,
    repo=settings.BORG_ROOT,
    archive=None,
    target_database=db._DEFAULT_DATABASE,
    force=False,
):
    """Restore the library files, media files and database to the state given in the borg repo at path REPO
    using archive ARCHIVE. The target_database argument is for testing so a different database can be used to
    make sure the database is getting restored properly"""
    if not force:
        confirm("Are you sure you want to restore the database and all file content (y/n)? ")
    with tempfile.TemporaryDirectory(dir=settings.SHARE_DIR) as working_directory:
        _restore(
            ctx,
            repo,
            archive=archive,
            working_directory=working_directory,
            target_database=target_database,
        )
