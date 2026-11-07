"""Reject competing writers conservatively, including stopped restart-policy containers."""

import json
from pathlib import Path
import subprocess

from storage_isolation import paths_overlap


def conflicts(containers, project, roots, project_directory):
    roots = [Path(root).resolve() for root in roots]
    project_directory = Path(project_directory).resolve()
    for container in containers:
        if (
            container["project"] == project
            and container.get("working_dir")
            and Path(container["working_dir"]).resolve() == project_directory
        ):
            continue
        if container["status"] not in ("running", "restarting", "paused") and container["restart"] in ("", "no"):
            continue
        for mount in container["mounts"]:
            if mount.get("Type") != "bind" or not mount.get("RW"):
                continue
            source = Path(mount["Source"]).resolve()
            if any(paths_overlap(source, root) for root in roots):
                yield f"{container['name']}: project={container['project'] or 'unlabelled'}, working_dir={container.get('working_dir') or 'unknown'}, state={container['status']}, restart={container['restart']}, writable={source}"


def storage_layout():
    result = subprocess.run(
        ["bash", str(Path(__file__).with_name("storage-layout.sh")), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def inspect_conflicts(docker, project, layout, project_directory):
    ids = subprocess.check_output([*docker, "ps", "-aq"], text=True, stderr=subprocess.PIPE).split()
    containers = []
    if ids:
        template = '{"name":{{json .Name}},"project":{{json (index .Config.Labels "com.docker.compose.project")}},"working_dir":{{json (index .Config.Labels "com.docker.compose.project.working_dir")}},"status":{{json .State.Status}},"restart":{{json .HostConfig.RestartPolicy.Name}},"mounts":{{json .Mounts}}}'
        output = subprocess.check_output([*docker, "inspect", "--format", template, *ids], text=True, stderr=subprocess.PIPE)
        containers = [json.loads(line) for line in output.splitlines()]
    roots = [layout[key] for key in ("shared", "postgres", "logs", "backups")]
    return list(conflicts(containers, project, roots, project_directory))

