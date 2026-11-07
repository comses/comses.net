"""Storage isolation rules shared by candidate and rendered Compose checks."""

from pathlib import Path


def postgres_isolation_errors(config, postgres_root):
    """Only db may bind the PostgreSQL root, its ancestors or descendants."""
    postgres = Path(postgres_root).resolve()
    errors = []
    for name, service in config.get("services", {}).items():
        if name == "db":
            continue
        for mount in service.get("volumes", []):
            if mount.get("type") != "bind" or not mount.get("source"):
                continue
            source = Path(mount["source"]).resolve()
            if source == postgres or source in postgres.parents or postgres in source.parents:
                errors.append(
                    f"{name}:{mount.get('target', '?')} bind {mount['source']} "
                    "exposes PostgreSQL data; only db may mount it"
                )
    return errors
