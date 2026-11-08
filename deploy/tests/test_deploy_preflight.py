"""Unified preflight sequencing, aggregation and non-disclosure contracts."""

import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).parents[1] / "scripts/deploy-preflight"
module = runpy.run_path(str(SCRIPT))
check = module["check"]
config_errors = module["configuration_errors"]


def layout():
    return dict(
        app="/srv/apps/comses",
        shared="/srv/apps/comses/docker/shared",
        postgres="/srv/apps/comses/docker/pgdata",
        logs="/srv/logs/comses",
        backups="/srv/backups/comses",
        secrets="/srv/apps/comses/docker/secrets",
        compose_files=["base.yml", "staging.yml", "prod.yml"],
    )


def config():
    paths = layout()
    return dict(
        name="comses",
        services={
            "db": {"volumes": [{"type": "bind", "source": paths["postgres"], "target": "/var/lib/postgresql/data"}]},
            "redis": {"volumes": [{"type": "bind", "source": paths["shared"] + "/redis", "target": "/data"}]},
            "server": {
                "environment": {"DJANGO_SETTINGS_MODULE": "core.settings.production"},
                "volumes": [
                    {"type": "bind", "source": paths["shared"], "target": "/shared"},
                    {"type": "bind", "source": paths["logs"], "target": "/shared/logs"},
                ],
            },
        },
    )


class PreflightTests(unittest.TestCase):
    def test_configuration_rejects_wrong_storage_even_if_directories_exist(self):
        value = config()
        value["services"]["db"]["volumes"][0]["source"] = "/other/pgdata"
        self.assertIn("db:/var/lib/postgresql/data", config_errors(value, "prod", layout())[0])

    def test_required_data_mounts_must_be_writable(self):
        for service, index in (("db", 0), ("redis", 0), ("server", 0), ("server", 1)):
            with self.subTest(service=service, index=index):
                value = config()
                mount = value["services"][service]["volumes"][index]
                mount["read_only"] = True
                self.assertEqual(
                    config_errors(value, "prod", layout()),
                    [f"{service}:{mount['target']} must be writable"],
                )
                mount["read_only"] = False
                self.assertEqual(config_errors(value, "prod", layout()), [])

    def test_configuration_rejects_wrong_application_environment(self):
        self.assertTrue(config_errors(config(), "staging", layout()))
        self.assertEqual(config_errors(config(), "prod", layout()), [])

    def exercise(self, *, storage_status=0, conflicts=None, invalid_config=False):
        output = io.StringIO()
        response = config()
        if invalid_config:
            response["services"]["server"]["environment"] = {}
        with patch.dict(os.environ, {"DEPLOY_ENVIRONMENT": "prod", "DOCKER": "sudo docker"}, clear=True):
            with patch.dict(check.__globals__, candidate=lambda *a: response):
                with patch.dict(
                    module["ownership"].__dict__, storage_layout=layout, inspect_conflicts=lambda *a: conflicts or []
                ):
                    with patch(
                        "subprocess.run",
                        return_value=subprocess.CompletedProcess([], storage_status, "", "storage diagnostic"),
                    ) as call:
                        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                            status = check()
        self.assertEqual(call.call_args.kwargs["env"]["COMSES_PREFLIGHT_READ_ONLY"], "true")
        return status, output.getvalue()

    def test_aggregates_independent_failures(self):
        status, output = self.exercise(storage_status=1, conflicts=["competing writer"], invalid_config=True)
        self.assertEqual(status, 1)
        for invariant in ("storage layout", "candidate identity", "storage ownership"):
            self.assertIn("FAIL " + invariant, output)

    def test_success_reports_all_checks(self):
        status, output = self.exercise()
        self.assertEqual(status, 0)
        self.assertEqual(output.count("PASS "), 3)

    def test_render_failure_never_echoes_resolved_secrets(self):
        output = io.StringIO()
        with (
            patch.dict(os.environ, {"DEPLOY_ENVIRONMENT": "prod"}, clear=True),
            patch.dict(module["ownership"].__dict__, storage_layout=layout),
        ):
            with patch.dict(
                check.__globals__,
                candidate=lambda *a: (_ for _ in ()).throw(subprocess.CalledProcessError(1, [], stderr="SENSITIVE")),
            ):
                with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")):
                    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                        self.assertEqual(check(), 1)
        self.assertNotIn("SENSITIVE", output.getvalue())

    def test_selected_source_uses_canonical_project_and_same_docker(self):
        with patch("subprocess.check_output", return_value=json.dumps(config())) as call:
            module["candidate"](["docker", "--context", "selected"], layout(), source_root="/tmp/release")
        args = call.call_args.args[0]
        self.assertEqual(args[:5], ["docker", "--context", "selected", "compose", "--project-directory"])
        self.assertEqual(args[5], os.getcwd())
        self.assertIn("/tmp/release/prod.yml", args)

    def test_final_check_uses_only_rendered_configuration(self):
        with patch("subprocess.check_output", return_value=json.dumps(config())) as call:
            module["candidate"](["docker"], layout(), rendered="docker-compose.yml")
        args = call.call_args.args[0]
        self.assertEqual(args.count("-f"), 1)
        self.assertNotIn("base.yml", args)

    def test_shared_layout_respects_aliases_and_environment(self):
        script = SCRIPT.with_name("storage-layout.sh")
        with patch.dict(
            os.environ,
            {"DEPLOY_ENVIRONMENT": "prod", "COMSES_LOG_ROOT": "/logs-alias", "COMSES_BACKUPS_ROOT": "/backups-alias"},
            clear=True,
        ):
            actual = json.loads(subprocess.check_output(["bash", str(script), "--json"], text=True))
        self.assertEqual(actual["logs"], "/logs-alias")
        self.assertEqual(actual["backups"], "/backups-alias")
        self.assertEqual(actual["compose_files"], ["base.yml", "staging.yml", "prod.yml"])


class PostgresIsolationTests(unittest.TestCase):
    def assert_isolation(self, source, *, rejected, service="server", read_only=False):
        value = config()
        value["services"].setdefault(service, {"volumes": []})["volumes"].append(
            {"type": "bind", "source": source, "target": "/exposed-db", "read_only": read_only}
        )
        errors = config_errors(value, "prod", layout())
        self.assertEqual(bool(errors), rejected, errors)
        if rejected:
            self.assertIn(f"{service}:/exposed-db", errors[0])

        # Exercise the standalone verifier as well, with valid mounts for its
        # broader storage contract. Only Compose execution is mocked.
        verifier = runpy.run_path(str(SCRIPT.with_name("verify-compose-storage")))
        with patch.dict(os.environ, {"DEPLOY_ENVIRONMENT": "prod"}, clear=True):
            expected, _, _ = verifier["expected_mounts"]("prod")
            for (name, target), (path, readonly) in expected.items():
                volumes = value["services"].setdefault(name, {}).setdefault("volumes", [])
                volumes[:] = [mount for mount in volumes if mount["target"] != target]
                volumes.append({"type": "bind", "source": path, "target": target,
                                "read_only": readonly, "bind": {"create_host_path": False}})
            output = io.StringIO()
            with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, json.dumps(value), "")):
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                    status = verifier["main"]()
        self.assertEqual(status, int(rejected), output.getvalue())
        if rejected:
            self.assertIn("exposes PostgreSQL data", output.getvalue())

    def test_non_database_services_cannot_mount_postgres_paths(self):
        postgres = layout()["postgres"]
        for source in (postgres, str(Path(postgres).parent), postgres + "/base"):
            for service in ("server", "nginx", "worker"):
                for read_only in (False, True):
                    with self.subTest(source=source, service=service, read_only=read_only):
                        self.assert_isolation(source, rejected=True, service=service, read_only=read_only)

    def test_symlink_to_postgres_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            alias = Path(directory) / "database-alias"
            alias.symlink_to(layout()["postgres"], target_is_directory=True)
            self.assert_isolation(str(alias), rejected=True, read_only=True)

    def test_unrelated_sibling_is_allowed(self):
        self.assert_isolation(layout()["postgres"] + "-other", rejected=False)

    def test_database_service_can_mount_postgres(self):
        self.assert_isolation(layout()["postgres"], rejected=False, service="db")
