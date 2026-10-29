import fcntl
from datetime import datetime, timedelta, timezone
import os
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings
from invoke import Context, Result

from curator.invoke_tasks.borg import (
    MAX_PRUNE_BACKUP_AGE_SECONDS,
    _prune,
    _restore,
    _restore_database,
    backup,
    rotate_library_and_media_files,
    backup_all,
    borg_prune,
)


class BackupProtocolTests(TestCase):
    def setUp(self):
        run = patch.object(Context, "run", return_value=Result(stdout="test\n"))
        self.run = run.start()
        self.addCleanup(run.stop)

    def write_marker(self, backup_root, age=0):
        marker = Path(backup_root) / "last-successful-backup"
        timestamp = datetime.now(timezone.utc) - timedelta(seconds=age)
        marker.write_text(
            f"timestamp={timestamp.isoformat()}\narchive=test\n", encoding="ascii"
        )
        return marker

    def test_retention_preview_never_compacts(self):
        ctx = Context()
        with patch.object(ctx, "run") as run:
            _prune(ctx)
        run.assert_called_once()
        self.assertIn("borg prune --dry-run ", run.call_args.args[0])
        self.assertIn(
            "--keep-daily 14 --keep-weekly 8 --keep-monthly 12 --keep-yearly -1", run.call_args.args[0]
        )

    def test_configured_retention_is_used_for_preview_and_apply(self):
        policy = {"daily": "7", "weekly": "10", "monthly": "0", "yearly": "-1"}
        with override_settings(BORG_RETENTION=policy):
            _prune(Context())
            _prune(Context(), dry_run=False)
        commands = [call.args[0] for call in self.run.call_args_list]
        for command in commands[:2]:
            self.assertIn("--keep-daily 7 --keep-weekly 10 --keep-monthly 0 --keep-yearly -1", command)
        self.assertIn("--dry-run", commands[0])
        self.assertNotIn("--dry-run", commands[1])
        self.assertIn("borg compact", commands[2])

    def test_invalid_retention_prevents_repository_access(self):
        default = {"daily": 14, "weekly": 8, "monthly": 12, "yearly": -1}
        policies = [
            {**default, "weekly": value}
            for value in ("", "eight", "8; echo unsafe", "1.5", -2, 1.5, True, None)
        ]
        policies.extend(({}, {**default, "hourly": 1}, dict.fromkeys(default, 0)))
        for policy in policies:
            with self.subTest(policy=policy), override_settings(BORG_RETENTION=policy):
                with self.assertRaisesRegex(ValueError, "Invalid BORG_RETENTION"):
                    borg_prune(Context(), apply=True)
        self.run.assert_not_called()

    def test_policy_is_visible_even_when_backup_marker_is_missing(self):
        with tempfile.TemporaryDirectory() as backup_root:
            with override_settings(BACKUP_ROOT=backup_root), patch("builtins.print") as output:
                with self.assertRaisesRegex(RuntimeError, "without a successful"):
                    borg_prune(Context())
            self.assertIn("daily=14, weekly=8, monthly=12, yearly=unlimited", output.call_args.args[0])
        self.run.assert_not_called()

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
            self.write_marker(backup_root)
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
            self.write_marker(backup_root)
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
                patch(
                    "curator.invoke_tasks.borg._create_archive", return_value="archive-name"
                ) as borg_backup,
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

    def test_public_backup_refreshes_dump_under_lock_before_creating_archive(self):
        for command in (backup, backup_all):
            with self.subTest(command=command.name), tempfile.TemporaryDirectory() as backup_root:
                events = []

                def assert_locked(stage):
                    with (Path(backup_root) / ".backup.lock").open("a+") as lockfile:
                        with self.assertRaises(BlockingIOError):
                            fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    events.append(stage)
                    return "archive-name"

                with (
                    override_settings(BACKUP_ROOT=backup_root),
                    patch("curator.invoke_tasks.borg.db.backup", side_effect=lambda ctx: assert_locked("dump")),
                    patch(
                        "curator.invoke_tasks.borg._create_archive", side_effect=lambda ctx: assert_locked("archive")
                    ),
                ):
                    self.assertEqual(command(Context()), "archive-name")
                self.assertEqual(events, ["dump", "archive"])
                self.assertIn("archive=archive-name", (Path(backup_root) / "last-successful-backup").read_text())

    def test_standalone_backup_rejects_concurrent_operation(self):
        with tempfile.TemporaryDirectory() as backup_root:
            with (Path(backup_root) / ".backup.lock").open("w") as lockfile:
                fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with override_settings(BACKUP_ROOT=backup_root), patch("curator.invoke_tasks.borg.db.backup") as dump:
                    with self.assertRaisesRegex(RuntimeError, "cannot start backup"):
                        backup(Context())
                dump.assert_not_called()

    def test_failed_dump_create_or_verification_preserves_success_marker(self):
        for stage in ("dump", "create", "check"):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as root:
                root = Path(root)
                backup_root = root / "backups"
                (backup_root / "latest").mkdir(parents=True)
                for name in ("library", "media", "repository"):
                    (root / name).mkdir()
                marker = self.write_marker(backup_root)
                previous = (marker.read_bytes(), marker.stat().st_mtime_ns)
                events = []

                def fail_at(name):
                    events.append(name)
                    if name == stage:
                        raise RuntimeError(f"{stage} failed")

                def run(command, **kwargs):
                    fail_at("check" if "borg check" in command else "create")
                    return Result()

                self.run.side_effect = run
                with (
                    override_settings(
                        SHARE_DIR=root,
                        BACKUP_ROOT=backup_root,
                        BORG_ROOT=backup_root / "repo",
                        LIBRARY_ROOT=root / "library",
                        MEDIA_ROOT=root / "media",
                        REPOSITORY_ROOT=root / "repository",
                    ),
                    patch("curator.invoke_tasks.borg.db.backup", side_effect=lambda ctx: fail_at("dump")),
                ):
                    with self.assertRaisesRegex(RuntimeError, f"{stage} failed"):
                        backup(Context())
                self.assertEqual(events, ["dump", "create", "check"][: ["dump", "create", "check"].index(stage) + 1])
                self.assertEqual((marker.read_bytes(), marker.stat().st_mtime_ns), previous)

    def test_prune_requires_a_recent_successful_backup(self):
        with tempfile.TemporaryDirectory() as backup_root:
            self.write_marker(backup_root)
            with (
                override_settings(BACKUP_ROOT=backup_root),
                patch("curator.invoke_tasks.borg._prune") as prune,
            ):
                borg_prune(Context())

            prune.assert_called_once()

    def test_prune_rejects_a_stale_successful_backup(self):
        with tempfile.TemporaryDirectory() as backup_root:
            self.write_marker(backup_root, age=MAX_PRUNE_BACKUP_AGE_SECONDS + 1)

            with (
                override_settings(BACKUP_ROOT=backup_root),
                patch("curator.invoke_tasks.borg._prune") as prune,
            ):
                with self.assertRaisesRegex(RuntimeError, "too old"):
                    borg_prune(Context())

            prune.assert_not_called()

    def test_concurrent_operation_prevents_prune(self):
        with tempfile.TemporaryDirectory() as backup_root:
            self.write_marker(backup_root)
            lock_path = Path(backup_root) / ".backup.lock"
            with lock_path.open("w") as lockfile:
                fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with override_settings(BACKUP_ROOT=backup_root):
                    with self.assertRaisesRegex(RuntimeError, "cannot start prune"):
                        borg_prune(Context())

    def test_future_backup_marker_prevents_applying_retention(self):
        with tempfile.TemporaryDirectory() as backup_root:
            self.write_marker(backup_root, age=-3600)
            with (
                override_settings(BACKUP_ROOT=backup_root),
                patch("curator.invoke_tasks.borg._prune") as prune,
                patch("curator.invoke_tasks.borg.confirm") as confirm,
            ):
                with self.assertRaisesRegex(RuntimeError, "in the future"):
                    borg_prune(Context(), apply=True)
            prune.assert_not_called()
            confirm.assert_not_called()

    def test_mtime_does_not_determine_freshness(self):
        with tempfile.TemporaryDirectory() as backup_root:
            marker = self.write_marker(backup_root)
            os.utime(marker, (0, 0))
            with (
                override_settings(BACKUP_ROOT=backup_root),
                patch("curator.invoke_tasks.borg._prune") as prune,
            ):
                borg_prune(Context())
            prune.assert_called_once()

    def test_invalid_markers_prevent_retention(self):
        timestamp = datetime.now(timezone.utc).isoformat()
        for contents in (
            "",
            "archive=test\n",
            f"timestamp={timestamp}\n",
            "timestamp=invalid\narchive=test\n",
            "timestamp=2026-10-29T12:00:00\narchive=test\n",
            f"timestamp={timestamp}\narchive=\n",
            f"timestamp={timestamp}\narchive=test\narchive=other\n",
            f"timestamp={timestamp}\narchive=test\nunknown=value\n",
            f"timestamp={timestamp}\narchive=test\x00\n",
            f"timestamp={timestamp}\narchive=test\nmalformed",
        ):
            with (
                self.subTest(contents=contents),
                tempfile.TemporaryDirectory() as backup_root,
            ):
                (Path(backup_root) / "last-successful-backup").write_text(contents)
                with (
                    override_settings(BACKUP_ROOT=backup_root),
                    patch("curator.invoke_tasks.borg._prune") as prune,
                ):
                    with self.assertRaisesRegex(
                        RuntimeError, "invalid successful backup marker"
                    ):
                        borg_prune(Context(), apply=True)
                prune.assert_not_called()
        self.run.assert_not_called()

    def test_missing_archive_or_failed_listing_prevents_retention(self):
        for result, error in (
            (Result(stdout="test-other\n"), None),
            (None, RuntimeError("list failed")),
        ):
            with (
                self.subTest(error=error),
                tempfile.TemporaryDirectory() as backup_root,
            ):
                self.write_marker(backup_root)
                self.run.return_value = result
                self.run.side_effect = error
                with (
                    override_settings(BACKUP_ROOT=backup_root),
                    patch("curator.invoke_tasks.borg._prune") as prune,
                ):
                    with self.assertRaisesRegex(
                        RuntimeError, "missing from repository|list failed"
                    ):
                        borg_prune(Context(), apply=True)
                prune.assert_not_called()

    def test_backup_expiring_during_confirmation_prevents_apply(self):
        with tempfile.TemporaryDirectory() as backup_root:
            self.write_marker(backup_root)
            with (
                override_settings(BACKUP_ROOT=backup_root),
                patch("curator.invoke_tasks.borg._prune") as prune,
                patch(
                    "curator.invoke_tasks.borg.confirm",
                    side_effect=lambda prompt: self.write_marker(
                        backup_root, age=MAX_PRUNE_BACKUP_AGE_SECONDS + 1
                    ),
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "too old"):
                    borg_prune(Context(), apply=True)
            prune.assert_called_once()
            self.assertEqual(prune.call_args.kwargs, {})


class RestoreProtocolTests(TestCase):
    def populate_archive(self, root, repository=True, legacy=False):
        root = Path(root)
        for name in (Path(settings.LIBRARY_ROOT).name, Path(settings.MEDIA_ROOT).name):
            (root / name).mkdir()
        if repository:
            (root / Path(settings.REPOSITORY_ROOT).name).mkdir()
        dump_dir = root / Path(settings.BACKUP_ROOT).name / "latest"
        dump_dir.mkdir(parents=True)
        name = settings.DATABASES["default"]["NAME"]
        dump = dump_dir / (f"{name}.sql" if legacy else f"{name}.dump")
        dump.write_text("dummy dump contents")
        return dump

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
            self.populate_archive(working_directory)
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
            self.populate_archive(working_directory)
            with self.assertRaisesRegex(RuntimeError, "restore failed"):
                _restore(
                    ctx,
                    repo="repo",
                    archive="archive",
                    working_directory=working_directory,
                    target_database="default",
                )

        restore_files.assert_not_called()

    def test_incomplete_archive_is_rejected_before_database_or_file_changes(self):
        cases = ("library", "media", "dump", "empty-dump", "directory-dump", "file-repository", "symlink-media")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as root:
                work = Path(root) / "extracted"
                work.mkdir()
                dump = self.populate_archive(work)
                if case in ("library", "media"):
                    setting = settings.LIBRARY_ROOT if case == "library" else settings.MEDIA_ROOT
                    (work / Path(setting).name).rmdir()
                elif case == "dump":
                    dump.unlink()
                elif case == "empty-dump":
                    dump.write_text("")
                elif case == "directory-dump":
                    dump.unlink()
                    dump.mkdir()
                elif case == "file-repository":
                    repository = work / Path(settings.REPOSITORY_ROOT).name
                    repository.rmdir()
                    repository.write_text("not a directory")
                else:
                    media = work / Path(settings.MEDIA_ROOT).name
                    media.rmdir()
                    media.symlink_to(work / Path(settings.LIBRARY_ROOT).name, target_is_directory=True)
                ctx = Context()
                with (
                    override_settings(BACKUP_ROOT=Path(root) / Path(settings.BACKUP_ROOT).name),
                    patch("curator.invoke_tasks.borg.check_archive"),
                    patch("curator.invoke_tasks.borg._extract"),
                    patch("curator.invoke_tasks.borg._restore_database") as database,
                    patch("curator.invoke_tasks.borg._restore_files") as files,
                    patch.object(ctx, "run") as run,
                ):
                    with self.assertRaises((ValueError, FileNotFoundError)):
                        _restore(ctx, "repo", "archive", work, "default")
                database.assert_not_called()
                files.assert_not_called()
                run.assert_not_called()

    def test_legacy_dump_and_missing_repository_remain_supported(self):
        with tempfile.TemporaryDirectory() as root:
            dump = self.populate_archive(root, repository=False, legacy=True)
            ctx = Context()
            with (
                patch("curator.invoke_tasks.borg.check_archive"),
                patch("curator.invoke_tasks.borg._extract"),
                patch("curator.invoke_tasks.borg.db.restore_from_dump") as database,
                patch("curator.invoke_tasks.borg._restore_files") as files,
                patch.object(ctx, "run"),
            ):
                _restore(ctx, "repo", "archive", root, "default")
            self.assertEqual(database.call_args.kwargs["dumpfile"], str(dump))
            files.assert_called_once_with(root)

    def test_files_only_preflight_preserves_live_and_previous_trees(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            work = root / "extracted"
            work.mkdir()
            (work / "library").mkdir()
            for name in ("library", "media", "repository", ".latest"):
                (root / name).mkdir()
                (root / name / "sentinel").write_text(name)
            with override_settings(
                SHARE_DIR=root,
                PREVIOUS_SHARE_ROOT=root / ".latest",
                LIBRARY_ROOT=root / "library",
                MEDIA_ROOT=root / "media",
                REPOSITORY_ROOT=root / "repository",
            ):
                with self.assertRaisesRegex(ValueError, "expected directory"):
                    rotate_library_and_media_files(work)
            for name in ("library", "media", "repository", ".latest"):
                self.assertEqual((root / name / "sentinel").read_text(), name)

    def test_database_only_restore_rejects_empty_dump_before_replacement(self):
        with tempfile.TemporaryDirectory() as root:
            dump = self.populate_archive(root)
            dump.write_text("")
            with patch("curator.invoke_tasks.borg.db.restore_from_dump") as database:
                with self.assertRaisesRegex(ValueError, "nonempty database dump"):
                    _restore_database(Context(), root, "default")
            database.assert_not_called()
