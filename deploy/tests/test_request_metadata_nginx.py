"""Local Docker integration; no published ports, credentials, or live services.

Run: python3 deploy/tests/test_request_metadata_nginx.py
Uses cached nginx:stable (override NGINX_TEST_IMAGE with a deployed image digest).
"""

import json
import os
import re
import socket
import struct
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
IMAGE = os.environ.get("NGINX_TEST_IMAGE", "nginx:stable")


def docker(*args):
    result = subprocess.run(
        ["docker", *args], check=True, text=True, capture_output=True
    )
    return result.stdout + result.stderr


def receive_exact(connection, size):
    result = b""
    while len(result) < size:
        data = connection.recv(size - len(result))
        if not data:
            raise RuntimeError("incomplete uWSGI packet")
        result += data
    return result


class NginxMetadataTests(unittest.TestCase):
    def test_both_environments(self):
        print(
            docker(
                "run", "--rm", "--network", "none", "--entrypoint", "nginx", IMAGE, "-v"
            )
        )
        for environment in ("haproxy", "staging"):
            with (
                self.subTest(environment=environment),
                tempfile.TemporaryDirectory() as directory,
            ):
                self.check_environment(environment, Path(directory))

    def check_environment(self, environment, directory):
        source = ROOT / "deploy/nginx" / f"nginx-{environment}.conf"
        (directory / "static-secret").write_text("fixture")
        config = directory / "nginx.conf"
        config.write_text(source.read_text())
        mounts = [
            "-v",
            f"{config}:/etc/nginx/nginx.conf:ro",
            "-v",
            f"{ROOT / 'deploy/nginx/uwsgi_params'}:/etc/nginx/uwsgi_params:ro",
            "-v",
            f"{directory}:/shared/sockets",
            "-v",
            f"{directory}:/var/log/nginx",
            "-v",
            f"{directory}:/srv:ro",
        ]
        # Validate the unmodified checked-in config before changing only the listener.
        docker(
            "run",
            "--rm",
            "--network",
            "none",
            *mounts,
            "--entrypoint",
            "nginx",
            IMAGE,
            "-t",
        )
        config.write_text(
            re.sub(
                r"listen\s+80\s+proxy_protocol;",
                "listen unix:/shared/sockets/probe.sock proxy_protocol;",
                source.read_text(),
            )
        )
        name = "comses-metadata-test-" + uuid4().hex[:12]
        backend = socket.socket(socket.AF_UNIX)
        backend.bind(str(directory / "uwsgi.sock"))
        backend.listen()
        backend.settimeout(10)
        seen = []
        errors = []

        def upstream():
            try:
                for _ in range(4):
                    connection, _ = backend.accept()
                    with connection:
                        packet = receive_exact(connection, 4)
                        payload = receive_exact(
                            connection, struct.unpack("<BHB", packet)[1]
                        )
                        params = []
                        offset = 0
                        while offset < len(payload):
                            size = struct.unpack_from("<H", payload, offset)[0]
                            offset += 2
                            key = payload[offset : offset + size].decode()
                            offset += size
                            size = struct.unpack_from("<H", payload, offset)[0]
                            offset += 2
                            value = payload[offset : offset + size].decode()
                            offset += size
                            params.append((key, value))
                        seen.append(
                            [
                                value
                                for key, value in params
                                if key == "HTTP_X_REQUEST_ID"
                            ]
                        )
                        connection.sendall(
                            b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"
                        )
            except Exception as error:
                errors.append(error)

        thread = threading.Thread(target=upstream, daemon=True)
        thread.start()
        try:
            docker(
                "run",
                "-d",
                "--name",
                name,
                "--network",
                "none",
                *mounts,
                "--entrypoint",
                "nginx",
                IMAGE,
                "-g",
                "daemon off;",
            )
            for _ in range(100):
                if (directory / "probe.sock").exists():
                    break
                time.sleep(0.05)

            def probe(path, ids):
                connection = socket.socket(socket.AF_UNIX)
                connection.settimeout(5)
                with connection:
                    connection.connect(str(directory / "probe.sock"))
                    request = (
                        "PROXY TCP4 192.0.2.1 192.0.2.2 12345 80\r\n"
                        f"HEAD {path} HTTP/1.1\r\n"
                        "Host: example.com\r\nConnection: close\r\n"
                        "Cookie: synthetic-sensitive\r\n"
                        "Authorization: synthetic-sensitive\r\n"
                    )
                    request += "".join(f"X-Request-ID: {value}\r\n" for value in ids)
                    connection.sendall((request + "\r\n").encode())
                    response = b""
                    while data := connection.recv(4096):
                        response += data
                    return int(response.split()[1])

            valid = str(uuid4())
            self.assertEqual(
                probe("/dynamic-sensitive?secret=synthetic-sensitive", [valid]), 200
            )
            self.assertEqual(probe("/dynamic", [valid, valid]), 200)
            self.assertEqual(probe("/dynamic", ['malformed"synthetic-sensitive']), 200)
            self.assertEqual(probe("/static-secret", [valid]), 200)
            active = directory / "request-metadata.jsonl"
            for _ in range(100):
                if active.exists() and len(active.read_text().splitlines()) == 4:
                    break
                time.sleep(0.02)
            records = [json.loads(line) for line in active.read_text().splitlines()]
            self.assertEqual(len(records), 4)
            self.assertEqual(records[0]["request_id"], valid)
            self.assertEqual(records[1]["request_id"], "")
            self.assertEqual(records[2]["request_id"], "")
            self.assertIn(records[3]["upstream_status"], ("", "-"))
            self.assertIn(records[3]["upstream_response_time"], ("", "-"))
            fields = {
                "layer",
                "request_id",
                "status",
                "request_time",
                "upstream_response_time",
                "upstream_status",
                "request_length",
            }
            for record in records:
                self.assertEqual(set(record), fields)
                self.assertEqual(record["layer"], "nginx")
                self.assertGreater(record["request_length"], 0)
            self.assertNotIn("sensitive", active.read_text())
            archived = directory / "metadata.1"
            active.rename(archived)
            active.touch(mode=0o640)
            docker("exec", name, "nginx", "-s", "reopen")
            time.sleep(0.2)
            self.assertEqual(probe("/dynamic", []), 200)
            thread.join(timeout=5)
            self.assertFalse(errors, errors)
            self.assertEqual(seen, [[valid], [""], [""], [""]])
            for _ in range(100):
                if active.stat().st_size:
                    break
                time.sleep(0.02)
            self.assertEqual(len(active.read_text().splitlines()), 1)
            self.assertEqual(len(archived.read_text().splitlines()), 4)
            backend.close()
            self.assertEqual(probe("/dynamic", [valid]), 502)
            for _ in range(100):
                if len(active.read_text().splitlines()) == 2:
                    break
                time.sleep(0.02)
            error_record = json.loads(active.read_text().splitlines()[-1])
            self.assertEqual(error_record["request_id"], valid)
            self.assertEqual(error_record["status"], 502)
        finally:
            docker("rm", "-f", name)
            backend.close()


if __name__ == "__main__":
    unittest.main()
