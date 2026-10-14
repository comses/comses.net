"""Isolated Redis socket regression; cached redis:7-alpine, no existing data.

Run: python3 deploy/tests/test_redis_socket.py
No published ports; only synthetic PING requests.
"""

import json
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]


def docker(*args, check=True):
    return subprocess.run(
        ["docker", *args], check=check, text=True, capture_output=True
    )


class RedisSocketTests(unittest.TestCase):
    def test_missing_socket_fails_readiness_and_restart_rebinds(self):
        with tempfile.TemporaryDirectory(prefix="comses-redis-socket-") as directory:
            name = "comses-redis-socket-test-" + uuid4().hex[:12]
            socket_path = Path(directory) / "redis.sock"
            # Disposable data only. Root avoids host ownership changes.
            try:
                docker(
                    "run",
                    "-d",
                    "--name",
                    name,
                    "--network",
                    "none",
                    "--user",
                    "0:0",
                    "--entrypoint",
                    "redis-server",
                    "-v",
                    f"{directory}:/data",
                    "-v",
                    str(ROOT / "deploy/conf/redis.conf")
                    + ":/usr/local/etc/redis/redis.conf:ro",
                    "redis:7-alpine",
                    "/usr/local/etc/redis/redis.conf",
                    "--save",
                    "",
                    "--appendonly",
                    "no",
                )
                ping = (
                    "exec",
                    name,
                    "redis-cli",
                    "-e",
                    "-s",
                    "/data/redis.sock",
                    "ping",
                )
                for _ in range(100):
                    if (
                        socket_path.exists()
                        and docker(*ping, check=False).returncode == 0
                    ):
                        break
                    time.sleep(0.05)
                self.assertEqual(docker(*ping).stdout.strip(), "PONG")
                socket_path.unlink()
                self.assertEqual(
                    docker(
                        "inspect", "--format", "{{.State.Running}}", name
                    ).stdout.strip(),
                    "true",
                )
                self.assertNotEqual(docker(*ping, check=False).returncode, 0)
                docker("restart", "--time", "10", name)
                for _ in range(100):
                    if (
                        socket_path.exists()
                        and docker(*ping, check=False).returncode == 0
                    ):
                        break
                    time.sleep(0.05)
                self.assertEqual(docker(*ping).stdout.strip(), "PONG")
            finally:
                docker("rm", "-f", name, check=False)

    def test_compose_gates_server_on_socket_health_in_all_environments(self):
        with tempfile.TemporaryDirectory(prefix="comses-redis-compose-") as directory:
            environment = {
                "ES_VERSION": "8.15.5",
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
            # No checkout .env interpolation and no Docker daemon needed.
            for deployment in ("dev", "test", "staging", "prod"):
                files = ["-f", str(ROOT / "base.yml")]
                overlays = ["staging", "prod"] if deployment == "prod" else [deployment]
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
                    env={"PATH": "/usr/local/bin:/usr/bin:/bin", **environment},
                    check=True,
                    capture_output=True,
                    text=True,
                )
                services = json.loads(result.stdout)["services"]
                self.assertEqual(
                    services["redis"]["healthcheck"]["test"],
                    ["CMD", "redis-cli", "-e", "-s", "/data/redis.sock", "ping"],
                )
                self.assertEqual(
                    services["server"]["depends_on"]["redis"]["condition"],
                    "service_healthy",
                )


if __name__ == "__main__":
    unittest.main()
