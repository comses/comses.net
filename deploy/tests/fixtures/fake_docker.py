#!/usr/bin/env python3
"""Stateful Docker CLI test double for Makefile contract tests."""

import json
import os
from pathlib import Path
import sys


def append_record(arguments):
    release_version = os.environ.get("RELEASE_VERSION")
    environment_file = Path(".env")
    if release_version is None and environment_file.exists():
        for line in environment_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("RELEASE_VERSION="):
                release_version = line.partition("=")[2]
                break

    with Path(os.environ["FAKE_DOCKER_LOG"]).open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps(
                {
                    "args": arguments,
                    "project_name": os.environ.get("COMPOSE_PROJECT_NAME"),
                    "release_version": release_version,
                }
            )
            + "\n"
        )


def compose_command(arguments):
    if not arguments or arguments[0] != "compose":
        return arguments
    index = 1
    options_with_values = {"--project-directory", "--project-name", "-f", "-p"}
    while index < len(arguments) and arguments[index] in options_with_values:
        index += 2
    return arguments[index:]


def increment(path):
    count_path = Path(path)
    count = int(count_path.read_text(encoding="ascii")) if count_path.exists() else 0
    count += 1
    count_path.write_text(str(count), encoding="ascii")
    return count


arguments = sys.argv[1:]
append_record(arguments)
command = compose_command(arguments[2:] if arguments[:1] == ["--context"] else arguments)

if os.environ.get("FAKE_PREFLIGHT_CONFIG"):
    if "config" in command:
        for index, argument in enumerate(arguments):
            if argument == "-f" and not Path(arguments[index + 1]).is_file():
                print("SENSITIVE render diagnostic", file=sys.stderr)
                raise SystemExit(24)
        if os.environ.get("FAKE_RENDER_FAIL"):
            print("SENSITIVE render diagnostic", file=sys.stderr)
            raise SystemExit(23)
        print(Path(os.environ["FAKE_PREFLIGHT_CONFIG"]).read_text())
    elif command[:1] == ["ps"]:
        print("fixture-container")
    elif command[:1] == ["inspect"]:
        print(Path(os.environ["FAKE_PREFLIGHT_CONTAINER"]).read_text())
    elif command[:1] in (["build"], ["pull"]):
        if not os.environ.get("FAKE_PREFLIGHT_ALLOW_BUILD"):
            raise SystemExit(25)
        if command[0] == "build":
            path = Path(os.environ["FAKE_PREFLIGHT_CONTAINER"])
            container = json.loads(path.read_text())
            container["working_dir"] = "/different/checkout"
            path.write_text(json.dumps(container))
    else:
        raise SystemExit(25)
    raise SystemExit(0)

if "config" in command:
    print("services: {}")
    if os.environ.get("FAKE_RENDER_FAIL"):
        raise SystemExit(23)
elif command[:4] == ["ps", "--status", "running", "--services"]:
    count = increment(os.environ["FAKE_DOCKER_PS_COUNT"])
    if count == 1 and os.environ.get("FAKE_REDIS_RUNNING", "1") == "1":
        print("redis")
    elif count > 1 and os.environ.get("FAKE_FINAL_RUNNING"):
        print(os.environ["FAKE_FINAL_RUNNING"])
elif command[:1] == ["exec"] and "SAVE" in command:
    if os.environ.get("FAKE_REDIS_SAVE_FAIL") == "1":
        raise SystemExit(1)
    print(os.environ.get("FAKE_REDIS_SAVE_RESPONSE", "OK"))
elif command[:3] == ["ps", "--all", "--quiet"]:
    container_ids = os.environ.get("FAKE_CONTAINER_IDS", "").split()
    if container_ids:
        print("\n".join(container_ids))
elif arguments[:1] == ["inspect"]:
    print(f"/fake-container {os.environ.get('FAKE_EXIT_CODE', '0')}")
