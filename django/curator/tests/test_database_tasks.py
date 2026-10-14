import gzip
import os
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from invoke import Context

from curator.invoke_tasks.database import dump_migration, restore_from_dump


class MigrationDumpTaskTests(TestCase):
    @patch("curator.invoke_tasks.database.os.replace")
    @patch("curator.invoke_tasks.database.create_pgpass_file")
    @patch("curator.invoke_tasks.database.get_database_settings")
    @patch("curator.invoke_tasks.database.pathlib.Path.mkdir")
    def test_dump_migration_uses_timestamped_artifact_path(
        self, mkdir, get_database_settings, create_pgpass_file, replace
    ):
        get_database_settings.return_value = {
            "db_name": "comsesnet",
            "db_host": "db",
            "db_user": "comsesnet",
            "db_password": "secret",
        }
        ctx = Context()

        with (
            patch.dict(os.environ, {"DB_MIGRATION_TIMESTAMP": "20260523T220000"}, clear=False),
            patch.object(ctx, "run") as run_mock,
        ):
            dump_migration(ctx, force=True)

        create_pgpass_file.assert_called_once_with(ctx, db_key="default")
        mkdir.assert_called_once_with(parents=True, exist_ok=True)
        self.assertEqual(run_mock.call_count, 2)
        replace.assert_called_once()
        self.assertIn(
            "/migration-artifacts/20260523T220000/comsesnet.dump.tmp",
            run_mock.call_args_list[0].args[0],
        )
        self.assertIn("pg_restore --list", run_mock.call_args_list[1].args[0])

    @patch("curator.invoke_tasks.database.os.replace")
    @patch("curator.invoke_tasks.database.create_pgpass_file")
    @patch("curator.invoke_tasks.database.get_database_settings")
    @patch("curator.invoke_tasks.database.pathlib.Path.mkdir")
    def test_dump_is_not_promoted_when_validation_fails(
        self, mkdir, get_database_settings, create_pgpass_file, replace
    ):
        get_database_settings.return_value = {
            "db_name": "comsesnet",
            "db_host": "db",
            "db_user": "comsesnet",
            "db_password": "secret",
        }
        ctx = Context()

        with patch.object(ctx, "run", side_effect=[None, RuntimeError("invalid dump")]):
            with self.assertRaisesRegex(RuntimeError, "invalid dump"):
                dump_migration(ctx, force=True)

        replace.assert_not_called()


class MigrationRestoreTaskTests(TestCase):
    @patch("curator.invoke_tasks.database.drop")
    @patch("curator.invoke_tasks.database.get_database_settings")
    @patch("curator.invoke_tasks.database.pathlib.Path.is_file", return_value=True)
    def test_restore_from_dump_prefers_migration_artifact_when_timestamp_is_set(
        self, is_file, get_database_settings, drop
    ):
        get_database_settings.return_value = {
            "db_name": "comsesnet",
            "db_host": "db",
            "db_user": "comsesnet",
            "db_password": "secret",
        }
        ctx = Context()

        with (
            patch.dict(os.environ, {"DB_MIGRATION_TIMESTAMP": "20260523T220000"}, clear=False),
            patch.object(ctx, "run") as run_mock,
        ):
            restore_from_dump(ctx, force=True, migrate=False)

        drop.assert_called_once_with(ctx, database="default", create=True)
        run_mock.assert_called_once()
        self.assertIn(
            "/migration-artifacts/20260523T220000/comsesnet.dump",
            run_mock.call_args.args[0],
        )
        self.assertIn("pg_restore", run_mock.call_args.args[0])

    @patch("curator.invoke_tasks.database.drop")
    @patch("curator.invoke_tasks.database.get_database_settings")
    def test_legacy_dump_that_creates_database_restores_through_template1(self, get_database_settings, drop):
        get_database_settings.return_value = {
            "db_name": "comsesnet",
            "db_host": "db",
            "db_user": "comsesnet",
            "db_password": "secret",
        }
        ctx = Context()
        with tempfile.TemporaryDirectory() as directory:
            dumpfile = Path(directory) / "comsesnet.sql.gz"
            with gzip.open(dumpfile, "wt", encoding="utf-8") as stream:
                stream.write("CREATE DATABASE comsesnet WITH TEMPLATE = template0;\n\\connect comsesnet\n")
            with patch.object(ctx, "run") as run_mock:
                restore_from_dump(ctx, dumpfile=str(dumpfile), force=True, migrate=False)

        drop.assert_called_once_with(ctx, database="default", create=False)
        self.assertIn("-h db template1 comsesnet", run_mock.call_args.args[0])
        self.assertIn("--set=ON_ERROR_STOP=1", run_mock.call_args.args[0])

    @patch("curator.invoke_tasks.database.drop")
    @patch("curator.invoke_tasks.database.get_database_settings")
    def test_legacy_dump_rejects_a_different_created_database(self, get_database_settings, drop):
        get_database_settings.return_value = {
            "db_name": "comsesnet",
            "db_host": "db",
            "db_user": "comsesnet",
            "db_password": "secret",
        }
        ctx = Context()
        with tempfile.TemporaryDirectory() as directory:
            dumpfile = Path(directory) / "other.sql"
            dumpfile.write_text(
                "CREATE DATABASE other_database WITH TEMPLATE = template0;\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "not target"):
                restore_from_dump(ctx, dumpfile=str(dumpfile), force=True, migrate=False)

        drop.assert_not_called()
