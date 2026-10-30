"""Unprivileged contracts; never start Docker or touch an application database."""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
loader = SourceFileLoader("seed_workflow", str(ROOT / "deploy/scripts/provision-from-seed"))
workflow = module_from_spec(spec_from_loader(loader.name, loader))
loader.exec_module(workflow)
SEED = {
    "schema": 1,
    "kind": "borg",
    "repository_id": "a" * 64,
    "archive": "2026-10-23T03:46:22.656043Z",
    "archive_id": "b" * 64,
    "evidence_ref": "/operator/verified-seed.json",
}


class SeedProvisioningTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.args = SimpleNamespace(
            environment="staging",
            sudo_docker=True,
            target_id="instance-id",
            state_dir=self.root / "state",
            retry_restore=False,
        )
        self.provisioner = workflow.Provisioner(self.root, self.args)
        self.provisioner.call = Mock(return_value="")
        self.identity = {"seed": SEED, "release": "c" * 40, "filesystem_uuid": "filesystem"}

    def record(self, phases=None, identity=None):
        self.args.state_dir.mkdir(exist_ok=True)
        record = {"schema": 1, "identity": identity or self.identity, "phases": phases or {}}
        workflow.write_record(self.args.state_dir / "execution.json", record)
        return record

    def configure_calls(self):
        def call(argv, capture=False):
            if argv[:2] == ["git", "rev-parse"]:
                return self.identity["release"]
            if argv[0] == "findmnt":
                return "filesystem"
            return ""

        self.provisioner.call.side_effect = call

    def test_manifest_rejects_shell_fragments_and_unknown_fields(self):
        path = self.root / "seed.json"
        for change in (
            {"archive": 'archive"; touch /tmp/x'},
            {"archive": "$(id)"},
            {"repository_id": "short"},
            {"token": "not-allowed"},
            {"evidence_ref": "https://user:secret@example.invalid"},
        ):
            with self.subTest(change=change):
                path.write_text(json.dumps(SEED | change))
                with self.assertRaises(ValueError):
                    workflow.seed_identity(path)
        path.write_text(json.dumps(SEED))
        self.assertEqual(workflow.seed_identity(path), SEED)

    def test_oneoff_is_noninteractive_and_bypasses_init(self):
        self.provisioner.oneoff("server", "inv", "borg.restore", "--archive=" + SEED["archive"])
        argv = self.provisioner.call.call_args.args[0]
        self.assertIn("--interactive=false", argv)
        self.assertIn("--no-tty", argv)
        self.assertIn("--no-deps", argv)
        self.assertEqual(argv[argv.index("--entrypoint") + 1], "inv")
        with patch.object(workflow.subprocess, "run", return_value=SimpleNamespace(stdout="ok")) as run:
            workflow.run(["example"], cwd=self.root, env={}, capture=True)
        self.assertEqual(run.call_args.kwargs["stdin"], subprocess.DEVNULL)

    def test_production_selector_crosses_sudo_environment_reset(self):
        self.args.environment = "prod"
        provisioner = workflow.Provisioner(self.root, self.args)
        provisioner.call = Mock(return_value="")
        provisioner.oneoff("server", "inv", "borg.restore")
        command = provisioner.call.call_args.args[0]
        # Model sudo's env_reset by starting the command after sudo with no env.
        environment_command = command[2 : command.index("docker")]
        result = subprocess.run(
            [
                *environment_command,
                sys.executable,
                "-c",
                "import os; print(os.environ['COMSES_PROVISION_ENVIRONMENT'])",
            ],
            env={},
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "prod")

    def test_without_sudo_uses_the_selected_process_environment(self):
        self.args.environment = "prod"
        self.args.sudo_docker = False
        provisioner = workflow.Provisioner(self.root, self.args)
        self.assertEqual(provisioner.docker, ["docker"])
        self.assertEqual(provisioner.env["COMSES_PROVISION_ENVIRONMENT"], "prod")

    def test_recovery_settings_disable_sentry_before_importing_staging(self):
        import builtins
        import runpy

        staging = ModuleType("core.settings.staging")
        staging.HUEY = {"name": "comses", "immediate": True}
        staging.MIDDLEWARE = ["core.external_auth.ExternalAuthMiddleware", "allauth.account.middleware.AccountMiddleware"]
        original_import = builtins.__import__
        observed = []

        def import_module(name, *args, **kwargs):
            if name in ("core.settings.staging", "core.settings.production"):
                observed.append(os.environ["SENTRY_DSN"])
                return staging
            return original_import(name, *args, **kwargs)

        with (
            patch.dict(
                os.environ, {"SENTRY_DSN": "https://example.invalid/1", "COMSES_PROVISION_ENVIRONMENT": "staging"}
            ),
            patch("builtins.__import__", side_effect=import_module),
        ):
            result = runpy.run_path(str(ROOT / "django/core/settings/recovery.py"))
        self.assertEqual(observed, [""])
        self.assertEqual(result["EMAIL_BACKEND"], "django.core.mail.backends.locmem.EmailBackend")
        self.assertFalse(result["HUEY"]["immediate"])
        self.assertFalse(result["SECURE_SSL_REDIRECT"])
        self.assertEqual(result["DATACITE_DRY_RUN"], "true")
        self.assertFalse(result["GITHUB_CLIENT_SECRET"])
        self.assertFalse(result["EXTERNAL_AUTH_ENABLED"])
        self.assertEqual(result["MIDDLEWARE"][0], "core.external_auth.ExternalAuthMiddleware")

        with (
            patch.dict(os.environ, {"COMSES_PROVISION_ENVIRONMENT": "prod"}),
            patch("builtins.__import__", side_effect=import_module) as imported,
        ):
            result = runpy.run_path(str(ROOT / "django/core/settings/recovery.py"))
        self.assertTrue(any(call.args[0] == "core.settings.production" for call in imported.call_args_list))
        self.assertTrue(result["DATACITE_TEST_MODE"])
        self.assertFalse(result["EXTERNAL_AUTH_ENABLED"])
        self.assertEqual(result["MIDDLEWARE"][0], "core.external_auth.ExternalAuthMiddleware")

    def test_compose_profile_replaces_public_port_and_normal_init(self):
        import shutil

        if not shutil.which("docker"):
            self.skipTest("Docker Compose CLI unavailable; no daemon is needed")
        if subprocess.run(["docker", "compose", "version"], capture_output=True).returncode:
            self.skipTest("Docker Compose CLI unavailable")
        base = self.root / "base.json"
        services = {
            name: {"image": "example.invalid/fixture", "restart": "always"}
            for name in ("server", "vite", "nginx", *workflow.DATA_SERVICES)
        }
        services["nginx"]["ports"] = ["80:80"]
        services["server"]["command"] = ["/sbin/my_init"]
        base.write_text(json.dumps({"services": services}))
        result = subprocess.run(
            [
                "docker",
                "compose",
                "-p",
                "seed-test",
                "-f",
                str(base),
                "-f",
                str(ROOT / "recovery.yml"),
                "--profile",
                "*",
                "config",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        merged = json.loads(result.stdout)["services"]
        self.assertEqual(merged["server"]["entrypoint"], ["/bin/sleep"])
        self.assertEqual(merged["server"]["command"], ["infinity"])
        self.assertEqual(merged["server"]["environment"]["DJANGO_SETTINGS_MODULE"], "core.settings.recovery")
        self.assertEqual(len(merged["nginx"]["ports"]), 1)
        self.assertEqual(merged["nginx"]["ports"][0]["host_ip"], "127.0.0.1")
        renderer_loader = SourceFileLoader("web_profile", str(ROOT / "deploy/scripts/render-recovery-web"))
        renderer = module_from_spec(spec_from_loader(renderer_loader.name, renderer_loader))
        renderer_loader.exec_module(renderer)
        overlay = self.root / "web.json"
        overlay.write_text(renderer.render(ROOT, "staging", self.root)["compose.json"])
        command = result.args[:]
        command[command.index("--profile") : command.index("--profile")] = ["-f", str(overlay)]
        web = json.loads(subprocess.check_output(command, text=True))["services"]
        self.assertEqual(web["server"]["entrypoint"], ["/etc/service/django/run"])
        self.assertFalse(web["server"].get("command"))
        self.assertEqual(web["server"]["environment"]["DJANGO_SETTINGS_MODULE"], "core.settings.recovery")
        self.assertEqual(web["nginx"]["ports"], merged["nginx"]["ports"])
        self.assertEqual(web["server"]["restart"], "no")

    def test_prepare_reuses_normal_deployment_task_without_restore(self):
        self.provisioner.oneoff = Mock()
        self.provisioner.prepare()
        self.provisioner.oneoff.assert_called_once_with("server", "inv", "prepare")
        self.provisioner.call.assert_not_called()

    def test_recovery_web_reuses_deployment_configs_and_internal_downloads(self):
        loader = SourceFileLoader("recovery_web", str(ROOT / "deploy/scripts/render-recovery-web"))
        renderer = module_from_spec(spec_from_loader(loader.name, loader))
        loader.exec_module(renderer)
        for environment in ("staging", "prod"):
            with self.subTest(environment=environment):
                files = renderer.render(ROOT, environment, Path("/operator/web"))
                nginx = files["nginx.conf"]
                self.assertNotIn("listen      80 proxy_protocol", nginx)
                self.assertNotRegex(nginx, r"listen\s+80\s+proxy_protocol")
                self.assertIn("internal;", nginx)
                self.assertIn("alias /library;", nginx)
                self.assertIn("uwsgi_pass", nginx)
                self.assertNotIn("UWSGI_SCHEME       https;", files["uwsgi_params"])
                override = json.loads(files["compose.json"])
                self.assertEqual(override["services"]["server"]["entrypoint"], ["/etc/service/django/run"])
                self.assertEqual(override["services"]["server"]["command"], [])
                self.assertNotIn("ports", override["services"]["nginx"])

    def test_web_renderer_resumes_and_refuses_changed_output_before_writing(self):
        output = self.root / "web"
        argv = [
            sys.executable,
            str(ROOT / "deploy/scripts/render-recovery-web"),
            "--environment",
            "staging",
            "--output-dir",
            str(output),
            "--runtime-dir",
            "/operator/web",
        ]
        subprocess.run(argv, capture_output=True, check=True)
        original = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in output.iterdir()}
        subprocess.run(argv, capture_output=True, check=True)
        self.assertEqual(original, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in output.iterdir()})
        (output / "nginx.conf").unlink()
        (output / "sources.json").write_text("changed")
        result = subprocess.run(argv, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((output / "nginx.conf").exists())
        (output / "sources.json").unlink()
        (output / "sources.json").symlink_to(output / "uwsgi_params")
        self.assertNotEqual(subprocess.run(argv, capture_output=True).returncode, 0)
        self.assertEqual((output / "uwsgi_params").read_bytes(), original["uwsgi_params"][0])

    def test_restore_starts_only_data_and_always_names_archive(self):
        self.provisioner.oneoff = Mock()
        self.provisioner.restore(SEED)
        argv = self.provisioner.call.call_args.args[0]
        self.assertEqual(argv[-len(workflow.DATA_SERVICES) :], list(workflow.DATA_SERVICES))
        oneoff = self.provisioner.oneoff.call_args.args
        self.assertIn("--archive=" + SEED["archive"], oneoff)
        self.assertIn("--force", oneoff)
        self.assertNotIn("nginx", argv)

    def test_preview_never_creates_state_or_runs_docker(self):
        path = self.root / "seed.json"
        path.write_text(json.dumps(SEED))

        def run(argv, **kwargs):
            if argv[:2] == ["git", "rev-parse"]:
                return "c" * 40
            if argv[0] == "findmnt":
                return "filesystem"
            if argv[:2] == ["git", "diff"]:
                return ""
            if argv[:2] == ["git", "cat-file"]:
                return ""
            self.fail("Unexpected preview command: " + repr(argv))

        argv = [
            "--seed",
            str(path),
            "--release",
            "c" * 40,
            "--environment",
            "staging",
            "--target-id",
            "instance-id",
            "--state-dir",
            str(self.args.state_dir),
        ]
        with patch.object(workflow, "run", side_effect=run), redirect_stdout(io.StringIO()) as output:
            workflow.main(argv)
        self.assertEqual(json.loads(output.getvalue())["outcome"], "preview")
        self.assertFalse(self.args.state_dir.exists())
        with patch.object(workflow, "run", side_effect=run), redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                workflow.main([*argv, "--apply"])
        self.assertFalse(self.args.state_dir.exists())

        preview_identity = json.loads(output.getvalue())["identity"]
        self.record(identity=preview_identity)
        record_path = self.args.state_dir / "execution.json"
        before = record_path.read_bytes()
        with patch.object(workflow, "run", side_effect=run), redirect_stdout(io.StringIO()) as output:
            workflow.main(argv)
        self.assertEqual(json.loads(output.getvalue())["phase_status"]["restore"], "not-started")
        self.assertEqual(record_path.read_bytes(), before)
        self.record(identity=preview_identity | {"release": "different"})
        before = record_path.read_bytes()
        with patch.object(workflow, "run", side_effect=run):
            with self.assertRaisesRegex(ValueError, "identities changed"):
                workflow.main(argv)
        self.assertEqual(record_path.read_bytes(), before)

    def test_corrupt_phase_state_is_rejected(self):
        self.record(phases={"restore": "completed"})
        with self.assertRaisesRegex(ValueError, "unsupported schema or phase"):
            self.provisioner.apply(self.identity, ["restore"])
        self.provisioner.call.assert_not_called()

    def test_other_running_container_on_target_blocks_execution(self):
        self.provisioner.call.side_effect = [
            "container",
            json.dumps(
                {
                    "labels": {"com.docker.compose.project": "ordinary-production"},
                    "mounts": [{"Source": str(self.root / "docker/shared")}],
                }
            ),
        ]
        with self.assertRaisesRegex(ValueError, "Another running"):
            self.provisioner.refuse_application_writers()

    def test_same_project_server_blocks_but_data_service_is_allowed(self):
        for service, allowed in (("server", False), ("db", True)):
            self.provisioner.call.side_effect = [
                "container",
                json.dumps(
                    {
                        "labels": {
                            "com.docker.compose.project": self.provisioner.project,
                            "com.docker.compose.service": service,
                        },
                        "mounts": [],
                    }
                ),
            ]
            if allowed:
                self.provisioner.refuse_application_writers()
            else:
                with self.assertRaisesRegex(ValueError, "Stop application"):
                    self.provisioner.refuse_application_writers()

    def test_seed_identity_mismatch_fails_before_restore(self):
        self.provisioner.oneoff = Mock(
            return_value=json.dumps({"repository": {"id": "wrong"}, "archives": [{"id": SEED["archive_id"]}]})
        )
        with self.assertRaisesRegex(ValueError, "Working repository"):
            self.provisioner.verify_seed(SEED)
        self.provisioner.oneoff.return_value = json.dumps(
            {"repository": {"id": SEED["repository_id"]}, "archives": [{"id": "wrong"}]}
        )
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            self.provisioner.verify_seed(SEED)

    def test_major_is_discovered_and_mismatch_does_not_start_database(self):
        for major, dump_major in ((16, 16), (18, 18), (18, 16)):
            self.provisioner.call = Mock(
                return_value=json.dumps({"services": {"db": {"environment": {"POSTGRES_DB": "comsesnet"}}}})
            )
            self.provisioner.verify_seed = Mock()
            self.provisioner.images = Mock(return_value={"db": "id"})

            def oneoff(service, entrypoint, *args, capture=False):
                if entrypoint == "postgres" or entrypoint == "pg_restore":
                    return f"{entrypoint} (PostgreSQL) {major}.9"
                if entrypoint == "borg":
                    return "borg application-selected"
                return json.dumps({"from database": f"{dump_major}.9", "by pg_dump": f"{dump_major}.9"})

            self.provisioner.oneoff = oneoff
            if major == dump_major:
                self.assertIn(str(major), self.provisioner.inspect(SEED)["versions"]["postgres"])
            else:
                with self.assertRaisesRegex(ValueError, "major mismatch"):
                    self.provisioner.inspect(SEED)
            for call in self.provisioner.call.call_args_list:
                self.assertNotIn("up", call.args[0])

    def test_execution_cannot_change_identities(self):
        self.record(identity=self.identity | {"release": "different"})
        with self.assertRaisesRegex(ValueError, "identities changed"):
            self.provisioner.apply(self.identity, ["configure"])
        self.provisioner.call.assert_not_called()

    def test_shared_sequence_resumes_without_repeating_restore(self):
        self.configure_calls()
        for phase in workflow.PHASES:
            setattr(self.provisioner, phase, Mock(return_value={"images": {}, "activation": "held"}))
        self.provisioner.images = Mock(return_value={})
        self.provisioner.verify_seed = Mock()
        with redirect_stdout(io.StringIO()):
            self.provisioner.apply(self.identity, workflow.PHASES)
            self.provisioner.apply(self.identity, workflow.PHASES)
        self.provisioner.restore.assert_called_once_with(SEED)
        self.assertEqual(self.provisioner.validate.call_count, 2)
        record = json.loads((self.args.state_dir / "execution.json").read_text())
        self.assertTrue(all(phase["outcome"] == "completed" for phase in record["phases"].values()))

    def test_dump_header_pipeline_drains_after_listing_and_rejects_failures(self):
        import shlex

        for name, program in {
            "borg": (
                "import os,sys; sys.stdout.buffer.write(b'x' * (8 * 1024 * 1024)); "
                "sys.exit(int(os.getenv('FAIL_EXTRACT', '0')))"
            ),
            "pg_restore": (
                "import os,sys; sys.stdin.buffer.read(1); "
                "print(';     Dumped from database version: 18.1'); "
                "print(';     Dumped by pg_dump version: 18.1'); sys.exit(int(os.getenv('FAIL_LIST', '0')))"
            ),
        }.items():
            path = self.root / name
            path.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + " -c " + shlex.quote(program) + "\n")
            path.chmod(0o755)
        env = dict(os.environ, PATH=str(self.root), FAIL_EXTRACT="0", FAIL_LIST="0")
        argv = [sys.executable, "-c", workflow.DUMP_METADATA, "/repo", "exact-archive", "comsesnet"]
        result = subprocess.run(argv, env=env, capture_output=True, text=True, check=True, timeout=15)
        self.assertEqual(json.loads(result.stdout)["from database"], "18.1")
        for failure in ("FAIL_EXTRACT", "FAIL_LIST"):
            with self.subTest(failure=failure):
                failed_env = env | {failure: "1"}
                result = subprocess.run(argv, env=failed_env, capture_output=True, text=True, timeout=15)
                self.assertNotEqual(result.returncode, 0)

    def test_failure_is_persisted_without_secret_output(self):
        self.configure_calls()
        self.provisioner.configure = Mock(
            side_effect=subprocess.CalledProcessError(1, ["example"], output="secret-must-not-be-recorded")
        )
        with redirect_stdout(io.StringIO()), self.assertRaises(subprocess.CalledProcessError):
            self.provisioner.apply(self.identity, ["configure"])
        record = (self.args.state_dir / "execution.json").read_text()
        self.assertEqual(json.loads(record)["phases"]["configure"]["outcome"], "failed")
        self.assertNotIn("secret", record)

    def test_interrupted_restore_needs_explicit_retry(self):
        phases = {phase: {"outcome": "completed", "result": {"images": {}}} for phase in workflow.PHASES[:3]}
        phases["restore"] = {"outcome": "running"}
        self.record(phases)
        self.configure_calls()
        self.provisioner.images = Mock(return_value={})
        self.provisioner.verify_seed = Mock()
        self.provisioner.restore = Mock(return_value={"activation": "held"})
        with self.assertRaisesRegex(ValueError, "retry-restore"):
            self.provisioner.apply(self.identity, ["restore"])
        self.provisioner.restore.assert_not_called()
        self.args.retry_restore = True
        with redirect_stdout(io.StringIO()):
            self.provisioner.apply(self.identity, ["restore"])
        self.provisioner.restore.assert_called_once_with(SEED)

    def test_changed_runtime_blocks_resume_and_validation_is_repeated(self):
        phases = {phase: {"outcome": "completed", "result": {"images": {}}} for phase in workflow.PHASES}
        self.record(phases)
        self.configure_calls()
        self.provisioner.verify_seed = Mock()
        self.provisioner.images = Mock(return_value={"changed": "image"})
        with self.assertRaisesRegex(ValueError, "Runtime image identities"):
            self.provisioner.apply(self.identity, ["validate"])
        self.provisioner.images.return_value = {}
        self.provisioner.validate = Mock(return_value={"activation": "held"})
        with redirect_stdout(io.StringIO()):
            self.provisioner.apply(self.identity, ["validate"])
        self.provisioner.validate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
