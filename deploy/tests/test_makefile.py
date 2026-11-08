"""Contract tests for Makefile deployment and shutdown commands."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
FAKE_DOCKER = ROOT / "deploy/tests/fixtures/fake_docker.py"
FAKE_NOOP = ROOT / "deploy/tests/fixtures/fake_noop.py"
FAKE_PREFLIGHT = ROOT / "deploy/tests/fixtures/fake_storage_preflight.py"


class MakefileContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory(prefix="comses-make-contract-")
        self.root = Path(self.temporary_directory.name)
        self.project = self.root / "physical checkout"
        self.alias = self.root / "logical-checkout"
        self.secrets = self.root / "secrets"
        self.shared = self.root / "shared"
        self.project.mkdir()
        self.secrets.mkdir()
        self.shared.mkdir()
        self.alias.symlink_to(self.project, target_is_directory=True)

        shutil.copy(ROOT / "Makefile", self.project / "Makefile")
        for name in (
            "config.mk",
            "base.yml",
            "dev.yml",
            "staging.yml",
            "test.yml",
            "prod.yml",
            "docker-compose.yml",
        ):
            (self.project / name).touch()
        (self.project / ".env").write_text("RELEASE_VERSION=fixture\n", encoding="utf-8")
        for name in (
            "db_password",
            ".pgpass",
            "django_secret_key",
            "download_analytics_hmac_key",
        ):
            (self.secrets / name).touch()

        scripts = self.project / "deploy/scripts"
        scripts.mkdir(parents=True)
        shutil.copy(FAKE_PREFLIGHT, scripts / "storage-preflight")
        shutil.copy(ROOT / "deploy/scripts/storage-layout.sh", scripts / "storage-layout.sh")
        shutil.copy(FAKE_NOOP, scripts / "envreplace")
        (scripts / "storage-preflight").chmod(0o755)
        (scripts / "envreplace").chmod(0o755)
        ownership = scripts / "deploy-preflight"
        ownership.write_text(
            "#!/usr/bin/env python3\nimport json, os, sys\n"
            'with open(os.environ["FAKE_DOCKER_LOG"], "a") as log:\n'
            '    log.write(json.dumps({"event": "ownership"}) + "\\n")\n'
            'with open(os.environ["FAKE_DOCKER_LOG"]) as log:\n'
            '    count = sum(json.loads(line).get("event") == "ownership" for line in log)\n'
            'fail_on = int(os.environ.get("FAKE_PREFLIGHT_FAIL_ON", "0"))\n'
            'sys.exit(int(os.environ.get("FAKE_OWNERSHIP_FAILURE", "0")) or count == fail_on)\n'
        )
        ownership.chmod(0o755)

        self.log = self.root / "docker.jsonl"
        self.ps_count = self.root / "docker-ps-count"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def make_arguments(self, target, deployment, entry=None):
        return [
            "make",
            "--no-print-directory",
            "-C",
            str(entry or self.project),
            target,
            f"DEPLOY_ENVIRONMENT={deployment}",
            f"COMSES_APP_ROOT={self.project}",
            f"COMSES_SHARED_ROOT={self.shared}",
            f"COMSES_POSTGRES_ROOT={self.root / 'pgdata'}",
            f"COMSES_LOG_ROOT={self.root / 'logs'}",
            f"COMSES_BACKUPS_ROOT={self.root / 'backups'}",
            f"COMSES_SECRETS_ROOT={self.secrets}",
            f"DOCKER=python3 {FAKE_DOCKER}",
            "SLEEP=true",
        ]

    def run_make(
        self,
        target,
        deployment="staging",
        *,
        entry=None,
        environment=None,
        check=True,
    ):
        self.log.write_text("", encoding="utf-8")
        self.ps_count.unlink(missing_ok=True)
        process_environment = os.environ.copy()
        for name in (
            "DOCKER_BUILD_FLAGS",
            "FAKE_RENDER_FAIL",
            "FAKE_REDIS_RUNNING",
            "FAKE_REDIS_SAVE_FAIL",
            "FAKE_REDIS_SAVE_RESPONSE",
            "FAKE_FINAL_RUNNING",
            "FAKE_CONTAINER_IDS",
            "FAKE_EXIT_CODE",
            "RELEASE_VERSION",
        ):
            process_environment.pop(name, None)
        process_environment.update(
            {
                "COMPOSE_PROJECT_NAME": "existing-stack",
                "FAKE_DOCKER_LOG": str(self.log),
                "FAKE_DOCKER_PS_COUNT": str(self.ps_count),
                **(environment or {}),
            }
        )
        result = subprocess.run(
            self.make_arguments(target, deployment, entry),
            env=process_environment,
            check=check,
            capture_output=True,
            text=True,
        )
        records = [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]
        return result, records

    def assert_compose_prefix(self, records):
        commands = []
        for record in records:
            if record.get("event") in ("preflight", "ownership"):
                commands.append(record)
                continue
            arguments = record["args"]
            if arguments[0] == "compose":
                self.assertEqual(
                    arguments[:3],
                    ["compose", "--project-directory", str(self.project)],
                )
                self.assertEqual(arguments.count("--project-directory"), 1)
                self.assertNotIn("--project-name", arguments)
                self.assertNotIn("-p", arguments)
                self.assertEqual(record["project_name"], "existing-stack")
                selected = arguments[3:]
                if "config" not in selected:
                    self.assertEqual(selected[:2], ["-f", "docker-compose.yml"])
                    self.assertEqual(selected.count("-f"), 1)
                    selected = selected[2:]
                commands.append(selected)
            else:
                commands.append(arguments)
        return commands

    def test_deploy_uses_physical_project_directory_in_every_environment(self):
        for deployment in ("dev", "test", "staging", "prod"):
            for entry in (self.project, self.alias):
                with self.subTest(deployment=deployment, entry=entry.name):
                    _, records = self.run_make("deploy", deployment, entry=entry)
                    self.assertEqual(records.pop(0), {"event": "ownership"})
                    commands = self.assert_compose_prefix(records)
                    files = ["-f", "base.yml"]
                    if deployment == "prod":
                        files += ["-f", "staging.yml", "-f", "prod.yml"]
                    else:
                        files += ["-f", f"{deployment}.yml"]
                    expected = [
                        files + ["config"],
                        ["build", "--pull", "--parallel"],
                        ["pull", "-q", "db", "redis", "elasticsearch"],
                    ]
                    if deployment != "dev":
                        expected.append(["pull", "-q", "nginx"])
                    expected += [
                        {"event": "ownership"},
                        ["up", "-d", "--quiet-pull"],
                        ["exec", "server", "inv", "prepare"],
                    ]
                    self.assertEqual(commands, expected)
                    self.assertFalse(
                        list(self.secrets.glob("borg_replication_*")),
                        "application recreated retired Borg push secrets",
                    )

    def test_deploy_pins_configuration_despite_discovery_overrides(self):
        (self.project / "docker-compose.override.yml").write_text(
            "services: {db: {image: unvalidated}}\n"
        )
        _, records = self.run_make(
            "deploy", "prod", environment={"COMPOSE_FILE": "unvalidated.yml"}
        )
        commands = self.assert_compose_prefix(records)
        self.assertIn(["up", "-d", "--quiet-pull"], commands)
        render = next(command for command in commands if "config" in command)
        self.assertEqual(
            render,
            ["-f", "base.yml", "-f", "staging.yml", "-f", "prod.yml", "config"],
        )

    def test_failed_render_preserves_previous_configuration(self):
        rendered = self.project / "docker-compose.yml"
        rendered.write_text("previous configuration\n")
        result, _ = self.run_make("build", environment={"FAKE_RENDER_FAIL": "1"}, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(rendered.read_text(), "previous configuration\n")
        self.assertEqual(list(self.project.glob("docker-compose.yml.*")), [])

    def test_render_creates_private_configuration(self):
        self.run_make("build")
        self.assertEqual((self.project / "docker-compose.yml").stat().st_mode & 0o777, 0o600)
        self.assertEqual(list(self.project.glob("docker-compose.yml.*")), [])

    def test_mixed_preflight_goals_fail_before_any_command(self):
        arguments = self.make_arguments("deploy-preflight", "prod") + ["deploy"]
        result = subprocess.run(arguments, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be the sole goal", result.stderr)
        self.assertFalse(self.log.exists())

    def test_layout_failure_stops_make_before_commands(self):
        (self.project / "deploy/scripts/storage-layout.sh").write_text("exit 17\n")
        result, records = self.run_make("deploy", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot resolve Compose overlays", result.stderr)
        self.assertEqual(records, [])

    def install_real_preflight(self):
        from deploy.tests.test_deploy_preflight import config
        scripts = self.project / "deploy/scripts"
        for name in ("deploy-preflight", "compose_ownership.py", "storage_isolation.py"):
            shutil.copy(ROOT / "deploy/scripts" / name, scripts / name)
        value = config()
        for service in value["services"].values():
            for mount in service["volumes"]:
                target = mount["target"]
                mount["source"] = str({
                    "/var/lib/postgresql/data": self.root / "pgdata",
                    "/data": self.shared / "redis",
                    "/shared": self.shared,
                    "/shared/logs": self.root / "logs",
                }[target])
        config_path = self.root / "candidate.json"
        config_path.write_text(json.dumps(value))
        container_path = self.root / "container.json"
        container_path.write_text(json.dumps({
            "name": "fixture-writer", "project": "comses", "working_dir": str(self.project),
            "status": "running", "restart": "always",
            "mounts": [{"Type": "bind", "RW": True, "Source": str(self.shared)}],
        }))
        return {"FAKE_PREFLIGHT_CONFIG": str(config_path),
                "FAKE_PREFLIGHT_CONTAINER": str(container_path)}

    def test_real_preflight_reads_selected_source_and_canonical_identity(self):
        environment = self.install_real_preflight()
        source = self.root / "candidate source"
        source.mkdir()
        for name in ("base.yml", "staging.yml", "prod.yml"):
            (source / name).touch()
        before = (self.project / ".env").read_bytes()
        result, records = self.run_make("deploy-preflight", "prod", environment={
            **environment, "COMPOSE_SOURCE_ROOT": str(source),
        })
        self.assertIn("Deployment preflight passed", result.stdout)
        commands = [record["args"] for record in records if "args" in record]
        self.assertEqual([command[3] for command in commands if command[0] == "compose"], ["-f"])
        self.assertIn(str(source / "prod.yml"), commands[0])
        self.assertEqual([command[0] for command in commands], ["compose", "ps", "inspect"])
        self.assertEqual((self.project / ".env").read_bytes(), before)

    def test_real_final_preflight_rejects_same_name_other_checkout(self):
        environment = self.install_real_preflight()
        # Run the actual Make deployment sequence, including its final --rendered argument.
        # The Docker fixture handles config/build/pull without starting services.
        environment["FAKE_PREFLIGHT_ALLOW_BUILD"] = "1"
        # Allow the early observation, then change identity after the build.
        result, records = self.run_make("deploy", "prod", environment=environment, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL storage ownership", result.stdout)
        configs = [record["args"] for record in records if "config" in record.get("args", [])]
        self.assertEqual(configs[-1][3:5], ["-f", "docker-compose.yml"])
        self.assertFalse(any("up" in record.get("args", []) for record in records))

    def test_real_preflight_render_error_is_safe_and_skips_identity_guess(self):
        environment = self.install_real_preflight()
        result, records = self.run_make("deploy-preflight", "prod", environment={
            **environment, "FAKE_RENDER_FAIL": "1",
        }, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("status 23", result.stderr)
        self.assertIn("candidate identity unavailable", result.stderr)
        self.assertNotIn("SENSITIVE", result.stdout + result.stderr)
        self.assertFalse(any("inspect" in record.get("args", []) for record in records))

    def test_real_preflight_missing_docker_identifies_executable(self):
        environment = self.install_real_preflight()
        arguments = self.make_arguments("deploy-preflight", "prod")
        missing = str(self.root / "missing-docker")
        arguments.append(f"DOCKER={missing}")
        result = subprocess.run(arguments, capture_output=True, text=True,
                                env={**os.environ, **environment, "FAKE_DOCKER_LOG": str(self.log)})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(missing, result.stderr)
        self.assertIn("candidate identity unavailable", result.stderr)

    def test_root_resolution_failure_is_not_an_empty_default(self):
        helper = self.project / "deploy/scripts/storage-layout.sh"
        helper.write_text('case "$1" in --compose-files) echo base.yml;; *) exit 19;; esac\n')
        arguments = [argument for argument in self.make_arguments("deploy", "prod")
                     if not argument.startswith("COMSES_APP_ROOT=")]
        environment = os.environ.copy()
        environment.pop("COMSES_APP_ROOT", None)
        result = subprocess.run(arguments, capture_output=True, text=True, env=environment)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot resolve COMSES_APP_ROOT", result.stderr)
        self.assertFalse(self.log.exists())

    def test_deploy_stops_before_pull_or_start_when_ownership_check_fails(self):
        result, records = self.run_make("deploy", "prod", environment={"FAKE_OWNERSHIP_FAILURE": "1"}, check=False)
        self.assertNotEqual(result.returncode, 0)
        commands = self.assert_compose_prefix(records)
        self.assertEqual(commands[-1], {"event": "ownership"})
        self.assertFalse(
            any(isinstance(command, list) and command[0] in ("build", "pull", "up") for command in commands)
        )

    def test_changed_conditions_after_build_block_service_start(self):
        result, records = self.run_make("deploy", "prod", environment={"FAKE_PREFLIGHT_FAIL_ON": "2"}, check=False)
        self.assertNotEqual(result.returncode, 0)
        commands = self.assert_compose_prefix(records)
        self.assertIn(["build", "--pull", "--parallel"], commands)
        self.assertNotIn(["up", "-d", "--quiet-pull"], commands)
        self.assertEqual(commands[-1], {"event": "ownership"})

    def test_preflight_does_not_generate_environment_or_secrets(self):
        before = (self.project / ".env").read_bytes()
        for path in self.secrets.iterdir():
            path.unlink()
        _, records = self.run_make("deploy-preflight", "prod")
        self.assertEqual(records, [{"event": "ownership"}])
        self.assertEqual((self.project / ".env").read_bytes(), before)
        self.assertEqual(list(self.secrets.iterdir()), [])

    def test_compose_render_uses_release_updated_in_same_invocation(self):
        bin_directory = self.root / "bin"
        bin_directory.mkdir()
        fake_git = bin_directory / "git"
        fake_git.write_text("#!/bin/sh\nprintf '%s\\n' new-release\n", encoding="utf-8")
        fake_git.chmod(0o755)

        envreplace = self.project / "deploy/scripts/envreplace"
        shutil.copy(ROOT / "deploy/scripts/envreplace", envreplace)
        envreplace.chmod(0o755)
        (self.project / ".env").write_text("RELEASE_VERSION=old-release\n", encoding="utf-8")

        _, records = self.run_make(
            "docker-compose.yml",
            environment={"PATH": f"{bin_directory}:{os.environ['PATH']}"},
        )

        config_record = next(record for record in records if "config" in record.get("args", []))
        self.assertEqual(config_record["release_version"], "new-release")
        self.assertEqual(
            (self.project / ".env").read_text(encoding="utf-8"),
            "RELEASE_VERSION=new-release\n",
        )

    def test_stop_uses_physical_project_directory_and_ordered_shutdown(self):
        for deployment in ("dev", "test", "staging", "prod"):
            for entry in (self.project, self.alias):
                with self.subTest(deployment=deployment, entry=entry.name):
                    _, records = self.run_make("stop", deployment, entry=entry)
                    commands = self.assert_compose_prefix(records)
                    expected = []
                    if deployment in ("staging", "prod"):
                        expected.append(["stop", "--timeout", "120", "nginx"])
                    expected += [
                        ["stop", "--timeout", "180", "server"],
                        ["ps", "--status", "running", "--services"],
                        [
                            "exec",
                            "-T",
                            "redis",
                            "redis-cli",
                            "-s",
                            "/data/redis.sock",
                            "SAVE",
                        ],
                        ["stop", "--timeout", "120"],
                        ["ps", "--status", "running", "--services"],
                        ["ps", "--all", "--quiet"],
                    ]
                    self.assertEqual(commands, expected)

    def test_stop_skips_redis_save_when_redis_is_stopped(self):
        _, records = self.run_make("stop", environment={"FAKE_REDIS_RUNNING": "0"})
        commands = self.assert_compose_prefix(records)
        self.assertFalse(any("SAVE" in command for command in commands))

    def test_stop_fails_closed_when_redis_save_fails(self):
        result, records = self.run_make(
            "stop",
            environment={"FAKE_REDIS_SAVE_FAIL": "1"},
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        commands = self.assert_compose_prefix(records)
        self.assertNotIn(["stop", "--timeout", "120"], commands)

    def test_stop_rejects_unexpected_redis_save_response(self):
        result, records = self.run_make(
            "stop",
            environment={"FAKE_REDIS_SAVE_RESPONSE": "QUEUED"},
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        commands = self.assert_compose_prefix(records)
        self.assertNotIn(["stop", "--timeout", "120"], commands)

    def test_stop_fails_when_a_service_remains_running(self):
        result, _ = self.run_make(
            "stop",
            environment={"FAKE_FINAL_RUNNING": "elasticsearch"},
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Services still running", result.stderr)

    def test_stop_reports_containers_forced_to_exit(self):
        result, records = self.run_make(
            "stop",
            environment={"FAKE_CONTAINER_IDS": "container-1", "FAKE_EXIT_CODE": "137"},
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required SIGKILL", result.stderr)
        commands = self.assert_compose_prefix(records)
        self.assertIn(
            [
                "inspect",
                "--format",
                "{{.Name}} {{.State.ExitCode}}",
                "container-1",
            ],
            commands,
        )

    def test_stop_refuses_to_regenerate_missing_compose_file(self):
        (self.project / "docker-compose.yml").unlink()
        result, records = self.run_make("stop", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("docker-compose.yml is required", result.stderr)
        self.assertEqual(records, [])

    def test_build_storage_prerequisites_are_environment_specific(self):
        for deployment in ("staging", "prod", "dev"):
            with self.subTest(deployment=deployment):
                arguments = self.make_arguments("build", deployment)
                arguments.insert(2, "-n")
                result = subprocess.run(
                    arguments,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                if deployment == "dev":
                    self.assertIn("chmod 0777", result.stdout)
                else:
                    self.assertNotIn("chmod 0777", result.stdout)

    def test_development_defaults_to_persistent_secret_directory(self):
        application_root = self.root / "application"
        (application_root / "docker/secrets").mkdir(parents=True)
        arguments = [
            "make",
            "--no-print-directory",
            "-n",
            "-C",
            str(self.project),
            "build",
            "DEPLOY_ENVIRONMENT=dev",
            f"COMSES_APP_ROOT={application_root}",
            f"COMSES_SHARED_ROOT={self.shared}",
            f"COMSES_POSTGRES_ROOT={self.root / 'pgdata'}",
        ]
        environment = os.environ.copy()
        environment.pop("COMSES_SECRETS_ROOT", None)
        result = subprocess.run(
            arguments,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        expected = application_root / "docker/secrets/download_analytics_hmac_key"
        self.assertIn(str(expected), result.stdout)
        self.assertNotIn(str(application_root / "build/secrets"), result.stdout)


if __name__ == "__main__":
    unittest.main()
