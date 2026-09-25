"""Isolated tests for the staging Borg replication command."""

import fcntl
import importlib.machinery
import importlib.util
import json
import os
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
    print(os.environ.get("FAKE_BORG_VERSION", "borg 1.2.8"))
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
            "COMSES_BORG_EXPECTED_VERSION": "1.2.8",
            "COMSES_BORG_REPLICATION_DELETE": "false",
        }
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
        self.assertNotIn("--delete-delay", rsync)
        self.assertIn("-F /dev/null", rsync[rsync.index("-e") + 1])
        self.assertIn("StrictHostKeyChecking=yes", rsync[rsync.index("-e") + 1])
        self.assertIn(str(self.key), rsync[rsync.index("-e") + 1])
        self.assertIn(str(self.known_hosts), rsync[rsync.index("-e") + 1])

    def test_deletion_requires_explicit_flag_and_propagates_failure(self):
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
        self.environment["FAKE_BORG_VERSION"] = "borg 2.0.0"
        with self.assertRaisesRegex(RuntimeError, "unexpected Borg version"):
            replicate.replicate(self.environment)
        self.assertFalse(self.log.exists())

    def test_waits_for_primary_backup_lock(self):
        with self.lock.open("a+") as lockfile:
            fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(TimeoutError, "primary backup lock"):
                replicate.replicate(self.environment)
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
