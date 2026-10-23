"""Render Compose without starting services or reading application data."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class BorgPullContractTests(unittest.TestCase):
    def test_application_has_no_push_credentials_in_any_environment(self):
        retired = {"borg_replication_ssh_key", "borg_replication_known_hosts"}
        with tempfile.TemporaryDirectory(prefix="comses-borg-compose-") as directory:
            environment = {
                "PATH": os.environ["PATH"],
                "ES_VERSION": "9.5.5",
                "RELEASE_VERSION": "fixture",
                "DB_USER": "fixture",
                "DB_NAME": "fixture",
                "UBUNTU_MIRROR": "fixture",
                "COMSES_APP_ROOT": str(ROOT),
                "COMSES_SHARED_ROOT": directory,
                "COMSES_POSTGRES_ROOT": directory,
                "COMSES_LOG_ROOT": directory,
                "COMSES_SECRETS_ROOT": directory,
            }
            for deployment in ("dev", "test", "staging", "prod"):
                with self.subTest(deployment=deployment):
                    overlays = (
                        ("staging", "prod") if deployment == "prod" else (deployment,)
                    )
                    files = ["-f", str(ROOT / "base.yml")]
                    for overlay in overlays:
                        files += ["-f", str(ROOT / f"{overlay}.yml")]
                    result = subprocess.run(
                        [
                            "docker",
                            "compose",
                            "--env-file",
                            "/dev/null",
                            *files,
                            "config",
                            "--format",
                            "json",
                        ],
                        cwd=directory,
                        env=environment,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    config = json.loads(result.stdout)
                    self.assertTrue(retired.isdisjoint(config.get("secrets", {})))
                    for service in config["services"].values():
                        for secret in service.get("secrets", []):
                            self.assertNotIn(secret["source"], retired)
                        self.assertFalse(
                            any(
                                key.startswith("COMSES_BORG_")
                                for key in service.get("environment", {})
                            )
                        )


if __name__ == "__main__":
    unittest.main()
