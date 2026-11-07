import contextlib
import io
import json
import os
import runpy
import unittest
from pathlib import Path
from unittest.mock import patch

preflight = runpy.run_path(str(Path(__file__).parents[1] / "scripts/compose-ownership-preflight"))
conflicts = preflight["conflicts"]


class OwnershipTests(unittest.TestCase):
    def check(
        self, *, project="old", status="running", restart="no", rw=True, source="/srv/apps/comses/docker/shared/redis"
    ):
        container = dict(
            name="old-redis",
            project=project,
            status=status,
            restart=restart,
            mounts=[dict(Type="bind", RW=rw, Source=source)],
        )
        return list(
            conflicts([container], "comses", ["/srv/apps/comses/docker/shared", "/srv/apps/comses/docker/pgdata"])
        )

    def test_running_foreign_writer_is_rejected(self):
        self.assertTrue(self.check())

    def test_stopped_restartable_writer_is_rejected(self):
        self.assertTrue(self.check(status="exited", restart="always"))

    def test_retired_container_is_allowed(self):
        self.assertFalse(self.check(status="exited"))

    def test_current_project_is_allowed(self):
        self.assertFalse(self.check(project="comses"))

    def test_read_only_backup_is_allowed(self):
        self.assertFalse(self.check(rw=False))

    def test_parent_mount_is_rejected(self):
        self.assertTrue(self.check(source="/srv/apps"))

    def test_similar_sibling_path_is_allowed(self):
        self.assertFalse(self.check(source="/srv/apps/comses/docker/shared-old"))

    def test_unlabelled_writer_is_rejected(self):
        self.assertTrue(self.check(project=None))


class PreflightCommandTests(unittest.TestCase):
    def invoke(self, *, environment=None, source=None, writable=True):
        container = dict(
            name="foreign-writer",
            project="other",
            status="running",
            restart="always",
            mounts=[dict(Type="bind", RW=writable, Source=source or "/unrelated")],
        )
        with patch.dict(
            os.environ,
            {"DEPLOY_ENVIRONMENT": "prod", "COMSES_APP_ROOT": "/srv/apps/comses", **(environment or {})},
            clear=True,
        ):
            with patch(
                "subprocess.check_output",
                side_effect=[json.dumps({"name": "comses"}), "container-id", json.dumps(container)],
            ) as command:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    preflight["main"]()
                return [call.args[0] for call in command.call_args_list]

    def test_all_commands_use_selected_docker_prefix(self):
        for value, prefix in [
            ("docker --context production", ["docker", "--context", "production"]),
            ("sudo docker", ["sudo", "docker"]),
            (
                '"/opt/docker tools/docker" --context "test context"',
                ["/opt/docker tools/docker", "--context", "test context"],
            ),
        ]:
            with self.subTest(command=value):
                calls = self.invoke(environment={"DOCKER": value})
                self.assertEqual(len(calls), 3)
                self.assertEqual([call[len(prefix)] for call in calls], ["compose", "ps", "inspect"])
                for call in calls:
                    self.assertEqual(call[: len(prefix)], prefix)
                self.assertEqual(
                    calls[0][len(prefix) :],
                    ["compose", "--project-directory", os.getcwd(), "config", "--format", "json"],
                )

    def test_default_docker_command(self):
        for call in self.invoke():
            self.assertEqual(call[0], "docker")

    def test_empty_command_fails_before_invocation(self):
        with (
            patch.dict(os.environ, {"DEPLOY_ENVIRONMENT": "prod", "DOCKER": " "}, clear=True),
            patch("subprocess.check_output") as command,
        ):
            with self.assertRaisesRegex(SystemExit, "empty"):
                preflight["main"]()
            command.assert_not_called()

    def test_canonical_backup_and_log_aliases_are_protected(self):
        for source in ["/srv/backups/comses/repo", "/srv/logs/comses/nginx", "/srv/backups", "/srv/logs/comses"]:
            with self.subTest(source=source), self.assertRaisesRegex(SystemExit, "obsolete containers"):
                self.invoke(source=source)

    def test_configured_backup_and_log_aliases_are_protected(self):
        for variable, source in [("COMSES_BACKUPS_ROOT", "/custom/backups"), ("COMSES_LOG_ROOT", "/custom/logs")]:
            with self.subTest(variable=variable), self.assertRaises(SystemExit):
                self.invoke(environment={variable: source}, source=source + "/nested")

    def test_read_only_alias_consumers_are_allowed(self):
        self.invoke(source="/srv/backups/comses/repo", writable=False)
        self.invoke(source="/srv/logs/comses/nginx", writable=False)

    def test_similar_alias_siblings_are_allowed(self):
        self.invoke(source="/srv/backups/comses-other")
        self.invoke(source="/srv/logs/comses-other")
