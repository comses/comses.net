import fcntl
import os
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from django.test import override_settings
from invoke import Context

from curator.invoke_tasks.borg import (
    MAX_PRUNE_BACKUP_AGE_SECONDS,
    _prune,
    _restore,
    backup_all,
    borg_prune,
)


class BackupProtocolTests(TestCase):
    def test_retention_preview_never_compacts(self):
        ctx = Context()
        with patch.object(ctx, "run") as run:
            _prune(ctx)
        run.assert_called_once()
        self.assertIn("borg prune --dry-run ", run.call_args.args[0])

    def test_retention_apply_compacts_only_after_successful_prune(self):
        ctx = Context()
        with patch.object(ctx, "run") as run:
            _prune(ctx, dry_run=False)
        self.assertEqual(run.call_count, 2)
        self.assertNotIn("--dry-run", run.call_args_list[0].args[0])
        self.assertIn("borg compact ", run.call_args_list[1].args[0])
        with patch.object(ctx, "run", side_effect=RuntimeError("prune failed")) as run:
            with self.assertRaisesRegex(RuntimeError, "prune failed"):
                _prune(ctx, dry_run=False)
        run.assert_called_once()

    def test_apply_previews_and_requires_operator_confirmation_under_lock(self):
        with tempfile.TemporaryDirectory() as backup_root:
            (Path(backup_root) / "last-successful-backup").write_text("archive=test\n")
            events = []

            def confirm_under_lock(prompt):
                with (Path(backup_root) / ".backup.lock").open("a+") as lockfile:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.assertIn("compact the local repository", prompt)
                events.append("confirm")

            with (
                override_settings(BACKUP_ROOT=backup_root),
                patch(
                    "curator.invoke_tasks.borg._prune",
                    side_effect=lambda ctx, **kwargs: events.append(
                        "apply" if kwargs.get("dry_run") is False else "preview"
                    ),
                ),
                patch(
                    "curator.invoke_tasks.borg.confirm", side_effect=confirm_under_lock
                ),
            ):
                borg_prune(Context(), apply=True)
            self.assertEqual(events, ["preview", "confirm", "apply"])

    def test_declined_confirmation_does_not_apply_retention(self):
        with tempfile.TemporaryDirectory() as backup_root:
            (Path(backup_root) / "last-successful-backup").write_text("archive=test\n")
            with (
                override_settings(BACKUP_ROOT=backup_root),
                patch("curator.invoke_tasks.borg._prune") as prune,
                patch(
                    "curator.invoke_tasks.borg.confirm",
                    side_effect=RuntimeError("Aborted"),
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "Aborted"):
                    borg_prune(Context(), apply=True)
            prune.assert_called_once()
            self.assertEqual(prune.call_args.kwargs, {})

    def test_prune_requires_a_successful_backup_marker(self):
        with tempfile.TemporaryDirectory() as backup_root:
            with (
                override_settings(BACKUP_ROOT=backup_root),
                patch("curator.invoke_tasks.borg._prune") as prune,
            ):
                with self.assertRaisesRegex(RuntimeError, "without a successful"):
                    borg_prune(Context())
            prune.assert_not_called()

    def test_success_marker_is_written_after_verified_backup(self):
        with tempfile.TemporaryDirectory() as backup_root:
            with (
                override_settings(BACKUP_ROOT=backup_root),
                patch("curator.invoke_tasks.borg.db.backup") as database_backup,
                patch("curator.invoke_tasks.borg.backup", return_value="archive-name") as borg_backup,
            ):
                backup_all(Context())

            database_backup.assert_called_once()
            borg_backup.assert_called_once()
            marker = Path(backup_root) / "last-successful-backup"
            self.assertIn("archive=archive-name", marker.read_text(encoding="ascii"))

    def test_concurrent_backup_fails_without_updating_success_marker(self):
        with tempfile.TemporaryDirectory() as backup_root:
            lock_path = Path(backup_root) / ".backup.lock"
            with lock_path.open("w") as lockfile:
                fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with override_settings(BACKUP_ROOT=backup_root):
                    with self.assertRaisesRegex(RuntimeError, "cannot start backup"):
                        backup_all(Context())

            self.assertFalse((Path(backup_root) / "last-successful-backup").exists())

    def test_prune_requires_a_recent_successful_backup(self):
        with tempfile.TemporaryDirectory() as backup_root:
            marker = Path(backup_root) / "last-successful-backup"
            marker.write_text("archive=test\n", encoding="ascii")
            with (
                override_settings(BACKUP_ROOT=backup_root),
                patch("curator.invoke_tasks.borg._prune") as prune,
            ):
                borg_prune(Context())

            prune.assert_called_once()

    def test_prune_rejects_a_stale_successful_backup(self):
        with tempfile.TemporaryDirectory() as backup_root:
            marker = Path(backup_root) / "last-successful-backup"
            marker.write_text("archive=test\n", encoding="ascii")
            old_timestamp = marker.stat().st_mtime - MAX_PRUNE_BACKUP_AGE_SECONDS - 1
            os.utime(marker, (old_timestamp, old_timestamp))

            with (
                override_settings(BACKUP_ROOT=backup_root),
                patch("curator.invoke_tasks.borg._prune") as prune,
            ):
                with self.assertRaisesRegex(RuntimeError, "too old"):
                    borg_prune(Context())

            prune.assert_not_called()

    def test_concurrent_operation_prevents_prune(self):
        with tempfile.TemporaryDirectory() as backup_root:
            marker = Path(backup_root) / "last-successful-backup"
            marker.write_text("archive=test\n", encoding="ascii")
            lock_path = Path(backup_root) / ".backup.lock"
            with lock_path.open("w") as lockfile:
                fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with override_settings(BACKUP_ROOT=backup_root):
                    with self.assertRaisesRegex(RuntimeError, "cannot start prune"):
                        borg_prune(Context())

    def test_future_backup_marker_prevents_applying_retention(self):
        with tempfile.TemporaryDirectory() as backup_root:
            marker = Path(backup_root) / "last-successful-backup"
            marker.write_text("archive=test\n", encoding="ascii")
            future_timestamp = marker.stat().st_mtime + 3600
            os.utime(marker, (future_timestamp, future_timestamp))
            with override_settings(BACKUP_ROOT=backup_root), patch(
                "curator.invoke_tasks.borg._prune"
            ) as prune, patch("curator.invoke_tasks.borg.confirm") as confirm:
                with self.assertRaisesRegex(RuntimeError, "in the future"):
                    borg_prune(Context(), apply=True)
            prune.assert_not_called()
            confirm.assert_not_called()


class RestoreProtocolTests(TestCase):
    def test_files_are_rotated_only_after_database_and_migrations_succeed(self):
        events = []
        ctx = Context()
        with (
            tempfile.TemporaryDirectory() as working_directory,
            patch(
                "curator.invoke_tasks.borg.check_archive",
                side_effect=lambda *args: events.append("check"),
            ),
            patch("curator.invoke_tasks.borg.delete_latest_uncompressed_backup"),
            patch(
                "curator.invoke_tasks.borg._extract",
                side_effect=lambda *args, **kwargs: events.append("extract"),
            ),
            patch(
                "curator.invoke_tasks.borg._restore_database",
                side_effect=lambda *args, **kwargs: events.append("database"),
            ),
            patch.object(ctx, "run", side_effect=lambda *args, **kwargs: events.append("migrate")),
            patch(
                "curator.invoke_tasks.borg._restore_files",
                side_effect=lambda *args: events.append("files"),
            ),
        ):
            _restore(
                ctx,
                repo="repo",
                archive="archive",
                working_directory=working_directory,
                target_database="default",
            )

        self.assertEqual(events, ["check", "extract", "database", "migrate", "files"])

    def test_files_are_not_rotated_when_database_restore_fails(self):
        ctx = Context()
        with (
            tempfile.TemporaryDirectory() as working_directory,
            patch("curator.invoke_tasks.borg.check_archive"),
            patch("curator.invoke_tasks.borg.delete_latest_uncompressed_backup"),
            patch("curator.invoke_tasks.borg._extract"),
            patch(
                "curator.invoke_tasks.borg._restore_database",
                side_effect=RuntimeError("restore failed"),
            ),
            patch("curator.invoke_tasks.borg._restore_files") as restore_files,
        ):
            with self.assertRaisesRegex(RuntimeError, "restore failed"):
                _restore(
                    ctx,
                    repo="repo",
                    archive="archive",
                    working_directory=working_directory,
                    target_database="default",
                )

        restore_files.assert_not_called()
