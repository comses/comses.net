"""Isolated Redis socket and Redis 7-to-8 persistence regressions.

Run: python3 deploy/tests/test_redis_socket.py
Requires cached redis:7-alpine and redis:8-alpine images.
No published ports; only disposable data and synthetic requests.
"""

import json
import os
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
            # Run as the caller so disposable state remains removable.
            try:
                docker(
                    "run",
                    "-d",
                    "--name",
                    name,
                    "--network",
                    "none",
                    "--user",
                    f"{os.getuid()}:{os.getgid()}",
                    "--entrypoint",
                    "redis-server",
                    "-v",
                    f"{directory}:/data",
                    "-v",
                    str(ROOT / "deploy/conf/redis.conf")
                    + ":/usr/local/etc/redis/redis.conf:ro",
                    "redis:8-alpine",
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

    def test_upgrade_preserves_persisted_data_and_accepts_new_writes(self):
        for appendonly in ("yes", "no"):
            with self.subTest(appendonly=appendonly):
                self._assert_upgrade_preserves_persisted_data(appendonly)

    def _assert_upgrade_preserves_persisted_data(self, appendonly):
        with tempfile.TemporaryDirectory(prefix="comses-redis-upgrade-") as directory:
            # Redis 7 writes the fixture; Redis 8 reads it, writes, and restarts.
            for index, image in enumerate(
                ("redis:7-alpine", "redis:8-alpine", "redis:8-alpine")
            ):
                with self.subTest(image=image, restart=index):
                    name = "comses-redis-upgrade-test-" + uuid4().hex[:12]
                    try:
                        docker(
                            "run",
                            "-d",
                            "--name",
                            name,
                            "--network",
                            "none",
                            "--user",
                            f"{os.getuid()}:{os.getgid()}",
                            "--entrypoint",
                            "redis-server",
                            "-v",
                            f"{directory}:/data",
                            "-v",
                            str(ROOT / "deploy/conf/redis.conf")
                            + ":/usr/local/etc/redis/redis.conf:ro",
                            image,
                            "/usr/local/etc/redis/redis.conf",
                            "--appendonly",
                            appendonly,
                        )

                        def cli(*args, check=True):
                            return docker(
                                "exec",
                                name,
                                "redis-cli",
                                "-e",
                                "--raw",
                                "-s",
                                "/data/redis.sock",
                                *args,
                                check=check,
                            )

                        for _ in range(100):
                            if cli("PING", check=False).returncode == 0:
                                break
                            time.sleep(0.05)
                        self.assertEqual(cli("PING").stdout.strip(), "PONG")
                        self.assertIn(
                            "redis_version:" + ("7." if index == 0 else "8."),
                            cli("INFO", "server").stdout,
                        )
                        if index == 0:
                            cli("SET", "cache", "cached-value")
                            cli("LPUSH", "queue", "queued-task")
                            cli("ZADD", "scheduled", "42", "scheduled-task")
                        else:
                            self.assertEqual(
                                cli("GET", "cache").stdout.strip(), "cached-value"
                            )
                            self.assertEqual(
                                cli("LRANGE", "queue", "0", "-1").stdout.strip(),
                                "queued-task",
                            )
                            self.assertEqual(
                                cli(
                                    "ZSCORE", "scheduled", "scheduled-task"
                                ).stdout.strip(),
                                "42",
                            )
                            if index == 1:
                                cli("SET", "after-upgrade", "new-value")
                            else:
                                self.assertEqual(
                                    cli("GET", "after-upgrade").stdout.strip(),
                                    "new-value",
                                )
                        self.assertEqual(cli("SAVE").stdout.strip(), "OK")
                        docker("stop", "--time", "120", name)
                        self.assertEqual(
                            docker(
                                "inspect", "--format", "{{.State.ExitCode}}", name
                            ).stdout.strip(),
                            "0",
                        )
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
                self.assertEqual(services["redis"]["image"], "redis:8-alpine")
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
