import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from library.models import Codebase, CodebaseRelease

from core import synthetic_seed
from django.core.management import call_command


class SyntheticSeedTest(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.overrides = override_settings(
            SHARE_DIR=str(self.root),
            LIBRARY_ROOT=str(self.root / "library"),
            MEDIA_ROOT=str(self.root / "media"),
            REPOSITORY_ROOT=str(self.root / "repository"),
            BACKUP_ROOT=str(self.root / "backups"),
            WAGTAILSEARCH_BACKENDS={"default": {"BACKEND": "wagtail.search.backends.database", "AUTO_UPDATE": False}},
        )
        self.overrides.enable()
        self.addCleanup(self.overrides.disable)

    def test_refuses_normal_settings_before_touching_database(self):
        with patch.object(synthetic_seed.connection.introspection, "table_names") as tables:
            with self.assertRaisesMessage(CommandError, "core.settings.seed"):
                synthetic_seed.preflight("comses_seed_test", self.root)
            tables.assert_not_called()

    @override_settings(SETTINGS_MODULE="core.settings.seed")
    def test_refuses_existing_database(self):
        with patch.dict(synthetic_seed.connection.settings_dict, NAME="comses_seed_test"):
            with self.assertRaisesMessage(CommandError, "no tables"):
                synthetic_seed.preflight("comses_seed_test", self.root)

    @override_settings(SETTINGS_MODULE="core.settings.seed")
    def test_refuses_relations_in_other_schemas(self):
        with (
            patch.dict(synthetic_seed.connection.settings_dict, NAME="comses_seed_test"),
            patch.object(synthetic_seed.connection.introspection, "table_names", return_value=[]),
            patch.object(synthetic_seed.connection, "cursor") as cursor,
        ):
            cursor.return_value.__enter__.return_value.fetchone.return_value = (True,)
            with self.assertRaisesMessage(CommandError, "outside the default schema"):
                synthetic_seed.preflight("comses_seed_test", self.root)

    @override_settings(SETTINGS_MODULE="core.settings.seed")
    def test_refuses_mismatched_database_and_storage(self):
        with patch.dict(synthetic_seed.connection.settings_dict, NAME="comses_seed_test"):
            with self.assertRaisesMessage(CommandError, "Database confirmation"):
                synthetic_seed.preflight("another_database", self.root)
            with override_settings(SETTINGS_MODULE="core.settings.seed", LIBRARY_ROOT="/shared/library"):
                with self.assertRaisesMessage(CommandError, "outside the confirmed seed layout"):
                    synthetic_seed.preflight("comses_seed_test", self.root)

    @override_settings(SETTINGS_MODULE="core.settings.seed")
    def test_refuses_existing_files_and_symlinks(self):
        with patch.dict(synthetic_seed.connection.settings_dict, NAME="comses_seed_test"):
            (self.root / "old.dump").write_bytes(b"private")
            with self.assertRaisesMessage(CommandError, "absent or empty"):
                synthetic_seed.preflight("comses_seed_test", self.root)
            link = self.root / "link"
            link.symlink_to(self.root)
            with self.assertRaisesMessage(CommandError, "no symlinks"):
                synthetic_seed.preflight("comses_seed_test", link)

    def test_preview_does_not_migrate_or_build(self):
        with (
            patch("core.synthetic_seed.preflight", return_value=self.root),
            patch("core.management.commands.build_synthetic_seed.call_command") as migrate,
            patch("core.synthetic_seed.build_fixtures") as build,
        ):
            call_command(
                "build_synthetic_seed",
                confirm_database="comses_seed_test",
                confirm_root=str(self.root),
                release="a" * 40,
            )
            migrate.assert_not_called()
            build.assert_not_called()
            self.assertEqual(list(self.root.iterdir()), [])

    def test_failed_build_retains_unapproved_report(self):
        from core.management.commands.build_synthetic_seed import Command

        options = {
            "confirm_database": "comses_seed_test",
            "confirm_root": str(self.root),
            "release": "a" * 40,
            "large_data_mib": 1,
        }
        with (
            patch("core.synthetic_seed.preflight"),
            patch("core.management.commands.build_synthetic_seed.call_command"),
            patch("core.synthetic_seed.build_fixtures", side_effect=RuntimeError("sensitive detail")),
        ):
            with self.assertRaises(CommandError):
                Command().build(self.root, options)
        report = json.loads((self.root / "seed-build.json").read_text())
        self.assertEqual(report["status"], "failed")
        self.assertFalse(report["publication_approved"])
        self.assertNotIn("sensitive detail", json.dumps(report))

    def test_build_has_real_source_versions_private_files_and_no_credentials(self):
        with patch("library.tasks.sync_release_submitter_to_discourse"):
            report = synthetic_seed.build_fixtures(1)
        self.assertEqual(Codebase.objects.public().count(), 12)
        self.assertEqual(CodebaseRelease.objects.count(), 14)
        self.assertFalse(CodebaseRelease.objects.filter(share_uuid__isnull=False).exists())
        self.assertFalse(CodebaseRelease.objects.filter(doi__isnull=False).exists())
        self.assertTrue(
            all(not user.has_usable_password() and not user.is_active for user in get_user_model().objects.all())
        )
        first_versions = [r for r in report["releases"] if r["codebase"] == "seed-public-01"]
        self.assertEqual([r["version"] for r in first_versions], ["1.0.0", "1.1.0"])
        self.assertNotEqual(first_versions[0]["archive_sha256"], first_versions[1]["archive_sha256"])
        private = CodebaseRelease.objects.get(codebase__identifier="seed-private")
        self.assertFalse(private.live)
        self.assertIn(b"population", (private.get_fs_api().sip_contents_dir / "code/model.py").read_bytes())
        self.assertGreaterEqual(report["large_input_bytes"], 1024 * 1024)
        for release in report["releases"]:
            if release["archive"]:
                self.assertEqual(synthetic_seed.sha256(self.root / release["archive"]), release["archive_sha256"])
        with self.assertRaisesMessage(CommandError, "Unexpected accounts/content"):
            synthetic_seed.build_fixtures(1)
