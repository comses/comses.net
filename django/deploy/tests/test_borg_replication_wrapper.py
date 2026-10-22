"""Isolated tests for the staging Borg replication command."""

import fcntl
import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "comses-borg-replicate"
loader = importlib.machinery.SourceFileLoader("comses_borg_replicate", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
replicate = importlib.util.module_from_spec(spec)
loader.exec_module(replicate)


class BorgReplicationWrapperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "backups" / "repo"
        self.repo.mkdir(parents=True)
        self.lock = self.repo.parent / ".backup.lock"
        self.key = self.root / "key"
        self.known_hosts = self.root / "known_hosts"
        self.key.write_text("test-key\n")
        self.known_hosts.write_text("test-host-key\n")
        self.key.chmod(0o600)
        self.known_hosts.chmod(0o600)
        self.log = self.root / "calls.jsonl"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self._executable(
            "borg",
            """#!/usr/bin/env python3
import json, os, subprocess, sys
if sys.argv[1:] == ["--version"]:
    print(os.environ.get("FAKE_BORG_VERSION", "borg 1.4.5"))
    sys.exit()
with open(os.environ["FAKE_LOG"], "a") as log:
    log.write(json.dumps(["borg", *sys.argv[1:]]) + "\\n")
sys.exit(subprocess.run(sys.argv[5:]).returncode)
""",
        )
        self._executable(
            "rsync",
            """#!/usr/bin/env python3
import json, os, sys
with open(os.environ["FAKE_LOG"], "a") as log:
    log.write(json.dumps(["rsync", *sys.argv[1:]]) + "\\n")
sys.exit(int(os.environ.get("FAKE_RSYNC_EXIT", "0")))
""",
        )
        self._executable("ssh", "#!/bin/sh\nexit 0\n")
        self.environment = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "FAKE_LOG": str(self.log),
            "COMSES_BORG_REPOSITORY": str(self.repo),
            "COMSES_BORG_REPLICATION_DESTINATION": replicate.DESTINATION,
            "COMSES_BORG_REPLICATION_LOCK_WAIT_SECONDS": "1",
            "COMSES_BORG_EXPECTED_VERSION": "1.4.5",
        }
        self.environment.pop("COMSES_BORG_REPLICATION_DELETE", None)
        patches = [
            patch.object(replicate, "REPOSITORY", self.repo),
            patch.object(replicate, "BACKUP_LOCK", self.lock),
            patch.object(replicate, "IDENTITY", self.key),
            patch.object(replicate, "KNOWN_HOSTS", self.known_hosts),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def _executable(self, name, content):
        path = self.bin / name
        path.write_text(content)
        path.chmod(0o755)

    def _calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_copy_holds_borg_lock_and_uses_strict_ssh(self):
        self.assertEqual(replicate.replicate(self.environment), 0)
        borg, rsync = self._calls()
        self.assertEqual(
            borg[:5], ["borg", "--lock-wait", "1", "with-lock", str(self.repo)]
        )
        self.assertEqual(rsync[-3:], ["--", f"{self.repo}/", replicate.DESTINATION])
        self.assertIn("--delete-delay", rsync)
        self.assertIn("-F /dev/null", rsync[rsync.index("-e") + 1])
        self.assertIn("StrictHostKeyChecking=yes", rsync[rsync.index("-e") + 1])
        self.assertIn(str(self.key), rsync[rsync.index("-e") + 1])
        self.assertIn(str(self.known_hosts), rsync[rsync.index("-e") + 1])

    def test_explicit_deletion_and_transfer_failure(self):
        self.environment["COMSES_BORG_REPLICATION_DELETE"] = "true"
        self.environment["FAKE_RSYNC_EXIT"] = "23"
        self.assertEqual(replicate.replicate(self.environment), 23)
        self.assertIn("--delete-delay", self._calls()[1])

    def test_rejects_missing_or_unsafe_secrets_and_destination(self):
        self.key.write_text("")
        with self.assertRaisesRegex(ValueError, "nonempty"):
            replicate.replicate(self.environment)
        self.key.write_text("test-key")
        self.key.chmod(0o622)
        with self.assertRaisesRegex(ValueError, "writable"):
            replicate.replicate(self.environment)
        self.key.chmod(0o600)
        self.key.unlink()
        self.key.symlink_to(self.known_hosts)
        with self.assertRaisesRegex(ValueError, "regular file"):
            replicate.replicate(self.environment)
        self.key.unlink()
        self.key.write_text("test-key")
        self.key.chmod(0o600)
        self.environment["COMSES_BORG_REPLICATION_DESTINATION"] = "-e sh"
        with self.assertRaisesRegex(ValueError, "fixed staging"):
            replicate.replicate(self.environment)
        self.assertFalse(self.log.exists())

    def test_rejects_wrong_repository_wait_and_empty_host_trust(self):
        for key, value in (
            ("COMSES_BORG_REPOSITORY", "/tmp/other-repository"),
            ("COMSES_BORG_REPLICATION_LOCK_WAIT_SECONDS", "0"),
            ("COMSES_BORG_REPLICATION_LOCK_WAIT_SECONDS", "-1"),
            ("COMSES_BORG_REPLICATION_LOCK_WAIT_SECONDS", "3601"),
            ("COMSES_BORG_REPLICATION_LOCK_WAIT_SECONDS", "invalid"),
            ("COMSES_BORG_REPLICATION_DELETE", "yes"),
            ("COMSES_BORG_REPLICATION_DELETE", "false"),
            ("COMSES_BORG_REPLICATION_DELETE", ""),
        ):
            with self.subTest(key=key, value=value):
                candidate = {**self.environment, key: value}
                with self.assertRaises(ValueError):
                    replicate.replicate(candidate)
        self.known_hosts.write_text("")
        with self.assertRaisesRegex(ValueError, "nonempty"):
            replicate.replicate(self.environment)
        self.assertFalse(self.log.exists())

    def test_rejects_wrong_borg_version(self):
        for version in ("1.2.8", "1.4.4", "2.0.0"):
            with self.subTest(version=version):
                self.environment["FAKE_BORG_VERSION"] = f"borg {version}"
                with self.assertRaisesRegex(RuntimeError, "unexpected Borg version"):
                    replicate.replicate(self.environment)
        self.assertFalse(self.log.exists())

    def test_waits_for_primary_backup_lock(self):
        with self.lock.open("a+") as lockfile:
            fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(TimeoutError, "primary backup lock"):
                replicate.replicate(self.environment)
        self.assertFalse(self.log.exists())


@unittest.skipUnless(
    all(shutil.which(program) for program in ("borg", "rsync", "ssh")),
    "requires real Borg 1.x, rsync, and OpenSSH (run in the server image)",
)
class BorgReplicationIntegrationTests(unittest.TestCase):
    def test_mirror_after_prune_and_compact_preserves_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            replica = root / "replica"
            snapshot = root / "snapshot"
            payload = root / "payload"
            key = root / "key"
            hosts = root / "known_hosts"
            for secret in (key, hosts):
                secret.write_text("synthetic fixture; local rsync uses no SSH\n")
                secret.chmod(0o600)
            environment = {
                **os.environ,
                "BORG_CACHE_DIR": str(root / "cache"),
                "BORG_SECURITY_DIR": str(root / "security"),
                "BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK": "yes",
                "BORG_RELOCATED_REPO_ACCESS_IS_OK": "yes",
                "COMSES_BORG_REPOSITORY": str(repo),
                "COMSES_BORG_REPLICATION_DESTINATION": str(replica),
                "COMSES_BORG_REPLICATION_LOCK_WAIT_SECONDS": "1",
            }
            environment.pop("COMSES_BORG_REPLICATION_DELETE", None)

            def borg(*arguments, security="security"):
                return subprocess.check_output(
                    ["borg", *map(str, arguments)],
                    env=environment | {
                        "BORG_SECURITY_DIR": str(root / security),
                        "BORG_CACHE_DIR": str(root / f"{security}-cache"),
                    },
                    cwd=root,
                    text=True,
                    stderr=subprocess.PIPE,
                )

            def extract(repository, archive, security):
                return subprocess.check_output(
                    [
                        "borg",
                        "extract",
                        "--stdout",
                        f"{repository}::{archive}",
                        "payload",
                    ],
                    env=environment | {
                        "BORG_SECURITY_DIR": str(root / security),
                        "BORG_CACHE_DIR": str(root / f"{security}-cache"),
                    },
                    stderr=subprocess.PIPE,
                )

            version = borg("--version").strip()
            if not version.startswith("borg 1."):
                self.skipTest("replication interface requires Borg 1.x")
            environment["COMSES_BORG_EXPECTED_VERSION"] = version.split()[1]
            borg("init", "--encryption=none", repo)
            first_payload = os.urandom(100000)
            payload.write_bytes(first_payload)
            borg(
                "create",
                "--timestamp",
                "2025-01-01T00:00:00",
                f"{repo}::first",
                "payload",
            )
            with (
                patch.object(replicate, "REPOSITORY", repo),
                patch.object(replicate, "BACKUP_LOCK", root / ".backup.lock"),
                patch.object(replicate, "IDENTITY", key),
                patch.object(replicate, "KNOWN_HOSTS", hosts),
                patch.object(replicate, "DESTINATION", str(replica)),
            ):
                self.assertEqual(replicate.replicate(environment), 0)
                borg("break-lock", replica)
                borg("check", "--verify-data", replica, security="replica-security")
                # A directory copy models the contents retained by a volume snapshot.
                shutil.copytree(replica, snapshot)
                snapshot_files = {
                    path.relative_to(snapshot)
                    for path in snapshot.rglob("*")
                    if path.is_file()
                }
                second_payload = os.urandom(100000)
                payload.write_bytes(second_payload)
                borg(
                    "create",
                    "--timestamp",
                    "2025-01-02T00:00:00",
                    f"{repo}::second",
                    "payload",
                )
                borg("prune", "--keep-last", "1", repo)
                borg("compact", repo)
                source_files = {
                    path.relative_to(repo)
                    for path in repo.rglob("*")
                    if path.is_file()
                }
                self.assertTrue(snapshot_files - source_files)
                self.assertEqual(replicate.replicate(environment), 0)
            borg("break-lock", replica)
            borg("check", "--verify-data", replica, security="replica-security")
            self.assertEqual(
                borg("list", "--short", replica, security="replica-security"),
                "second\n",
            )
            borg("check", "--verify-data", snapshot, security="snapshot-security")
            self.assertEqual(
                borg("list", "--short", snapshot, security="snapshot-security"),
                "first\n",
            )
            self.assertEqual(
                extract(replica, "second", "replica-security"),
                second_payload,
            )
            self.assertEqual(
                extract(snapshot, "first", "snapshot-security"),
                first_payload,
            )


if __name__ == "__main__":
    unittest.main()
