import os
import pathlib
import shutil
import tempfile

from django.conf import settings
from invoke import task

from . import database as db
from core.utils import confirm

DEFAULT_LIBRARY_BASENAME = os.path.basename(settings.LIBRARY_ROOT)
DEFAULT_MEDIA_BASENAME = os.path.basename(settings.MEDIA_ROOT)


@task(aliases=["init"])
def initialize_repo(ctx):
    if not os.path.exists(settings.BORG_ROOT):
        ctx.run(f"borg init --encryption=none {settings.BORG_ROOT}", echo=True)


@task(aliases=["list", "l"])
def borg_list(ctx):
    ctx.run(f"borg list {settings.BORG_ROOT}", echo=True, env=environment())


@task(aliases=["prune", "p"])
def borg_prune(ctx):
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


@task(aliases=["b"])
def backup(ctx):
    share = settings.SHARE_DIR
    repo = settings.BORG_ROOT
    # Borg recognizes {now} as the current timestamp
    #  http://borgbackup.readthedocs.io/en/stable/usage/help.html#borg-help-placeholders
    archive = "{utcnow}"
    library = os.path.relpath(settings.LIBRARY_ROOT, share)
    media = os.path.relpath(settings.MEDIA_ROOT, share)
    database = os.path.relpath(os.path.join(settings.BACKUP_ROOT, "latest"), share)

    error_msgs = []
    for p in (
        settings.LIBRARY_ROOT,
        settings.MEDIA_ROOT,
        os.path.join(settings.BACKUP_ROOT, "latest"),
    ):
        if not os.path.exists(p):
            error_msgs.append(f"Path {p} does not exist.")
    if error_msgs:
        raise IOError("Create archive failed. {}".format(" ".join(error_msgs)))

    with ctx.cd(share):
        ctx.run(
            f'borg create --stats --compression lz4 {repo}::"{archive}" {library} {media} {database}',
            echo=True,
            env=environment(),
        )


def delete_latest_uncompressed_backup(
    src_library=DEFAULT_LIBRARY_BASENAME, src_media=DEFAULT_MEDIA_BASENAME
):
    latest_dest_library = os.path.join(settings.PREVIOUS_SHARE_ROOT, src_library)
    latest_dest_media = os.path.join(settings.PREVIOUS_SHARE_ROOT, src_media)

    shutil.rmtree(latest_dest_library, ignore_errors=True)
    shutil.rmtree(latest_dest_media, ignore_errors=True)


def rotate_library_and_media_files(
    working_directory,
    src_library=DEFAULT_LIBRARY_BASENAME,
    src_media=DEFAULT_MEDIA_BASENAME,
):
    """
    Rotate the current library and media files

    Current library and media files are moved to the '.latest' folder in case of problems during the restore process.
    Files in .latest can be deleted if the restore was successful
    """
    print("rotating library and media files")
    delete_latest_uncompressed_backup(src_library=src_library, src_media=src_media)

    os.makedirs(settings.PREVIOUS_SHARE_ROOT, exist_ok=True)
    if os.path.exists(settings.LIBRARY_ROOT):
        shutil.move(settings.LIBRARY_ROOT, settings.PREVIOUS_SHARE_ROOT)
    if os.path.exists(settings.MEDIA_ROOT):
        shutil.move(settings.MEDIA_ROOT, settings.PREVIOUS_SHARE_ROOT)

    shutil.move(os.path.join(working_directory, src_library), settings.SHARE_DIR)
    shutil.move(os.path.join(working_directory, src_media), settings.SHARE_DIR)


def environment():
    return {
        "BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK": "yes",
        "BORG_RELOCATED_REPO_ACCESS_IS_OK": "yes",
    }


def _restore_files(working_directory):
    rotate_library_and_media_files(working_directory)


def _restore_database(ctx, working_directory, target_database):
    dumpfile_dir = pathlib.Path(
        os.path.join(
            working_directory, os.path.basename(settings.BACKUP_ROOT), "latest"
        )
    )
    if not dumpfile_dir.exists():
        raise IOError("dumpfile_dir {} not found".format(dumpfile_dir))
    dumpfile = str(list(dumpfile_dir.glob("comsesnet*"))[0])
    db.restore_from_dump(
        ctx,
        target_database=target_database,
        dumpfile=dumpfile,
        force=True,
    )


def _extract(ctx, repo, archive, paths=None):
    extract_cmd = 'borg extract {repo}::"{archive}"'.format(repo=repo, archive=archive)
    if paths:
        extract_cmd = "{} {}".format(
            extract_cmd, " ".join('"{}"'.format(p) for p in paths)
        )
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


def _restore(ctx, repo, archive, working_directory, target_database, progress=True):
    # Note that working directory is passed as argument. This makes it simpler to use either
    # a persistent directory (for testing and debugging) or a temporary directory
    if archive is None:
        archive = get_latest_borg_backup_archive_name(ctx, repo=repo)

    with ctx.cd(working_directory):
        delete_latest_uncompressed_backup()
        _extract(ctx, repo=repo, archive=archive)
        _restore_files(working_directory)
        _restore_database(
            ctx, working_directory=working_directory, target_database=target_database
        )


@task(aliases=["rf"])
def restore_files(ctx, repo=settings.BORG_ROOT, archive=None):
    confirm("Are you sure you want to restore all file content (y/n)? ")
    if archive is None:
        archive = get_latest_borg_backup_archive_name(ctx, repo=repo)

    with tempfile.TemporaryDirectory(dir=settings.SHARE_DIR) as working_directory:
        with ctx.cd(working_directory):
            delete_latest_uncompressed_backup()
            _extract(ctx, repo, archive)
            _restore_files(working_directory)


@task(aliases=["rdb"])
def restore_database(
    ctx, repo=settings.BORG_ROOT, archive=None, target_database=db._DEFAULT_DATABASE
):
    confirm("Are you sure you want to restore the database (y/n)? ")
    if archive is None:
        archive = get_latest_borg_backup_archive_name(ctx, repo=repo)

    with tempfile.TemporaryDirectory(dir=settings.SHARE_DIR) as working_directory:
        with ctx.cd(working_directory):
            _extract(ctx, repo, archive, ["backups"])
            _restore_database(
                ctx,
                working_directory=working_directory,
                target_database=target_database,
            )


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
        confirm(
            "Are you sure you want to restore the database and all file content (y/n)? "
        )
    with tempfile.TemporaryDirectory(dir=settings.SHARE_DIR) as working_directory:
        _restore(
            ctx,
            repo,
            archive=archive,
            working_directory=working_directory,
            target_database=target_database,
        )
        ctx.run("/code/manage.py migrate")
