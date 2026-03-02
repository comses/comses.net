---
applyTo: "**/tasks.py,**/invoke*"
---

## Overview

All operational tasks use Python **invoke** (not Make, not Fabric). Tasks live in `django/curator/invoke_tasks/` and are organized into namespaced collections. These are server-side tasks that run inside the Django Docker container.

> **AI agents must NEVER execute these tasks.** Document, read, and understand them only.

## Architecture

```
django/curator/invoke_tasks/
  __init__.py      # Collection assembly: ns.add_collection(borg), ns.add_collection(db), ...
  utils.py         # dj() helper (runs manage.py), env dict
  base.py          # Top-level: setup_site, collectstatic, test, server, prepare, clean
  borg.py          # Borg backup: backup, restore_files, restore_database, borg_list, borg_prune
  database.py      # DB: shell, backup, reset, drop, run_migrations, restore_from_dump
  es.py            # Elasticsearch: update_license
  docs.py          # Docs: run (make html)
  permissions.py   # Permissions: setup_editor_permissions
  drupal.py        # Legacy: import_drupal_data, import_codebase_files
```

## Task Groups

### Borg Backup (`borg.*`)
| Task | Alias | Description |
|------|-------|-------------|
| `borg.backup` | `borg.b` | Create Borg archive of library + media + DB dump |
| `borg.restore_files` | `borg.rf` | Restore library + media from archive |
| `borg.restore_database` | `borg.rdb` | Extract + restore DB dump from archive |
| `borg.borg_list` | `borg.l` | List available Borg archives |
| `borg.borg_prune` | `borg.p` | Prune old archives (14 daily, 4 weekly, 12 monthly) |
| `borg.initialize_repo` | `borg.init` | Initialize Borg repo (unencrypted) |

### Database (`db.*`)
| Task | Alias | Description |
|------|-------|-------------|
| `db.backup` | `db.b` | Run autopostgresqlbackup |
| `db.restore_from_dump` | `db.rfd` | Restore from .sql.gz dump file |
| `db.reset` | `db.r` | Drop + recreate + migrate |
| `db.drop` | `db.d` | Drop database (with `create=True` to recreate) |
| `db.run_migrations` | `db.init` | makemigrations + migrate |
| `db.shell` | `db.sh` | Open pgcli shell |

### Base (top-level)
| Task | Alias | Description |
|------|-------|-------------|
| `setup_site` | `ss` | Destructive site reset (removes root pages) |
| `collectstatic` | `cs` | Django collectstatic |
| `update_index` | `uindex` | Wagtail search index update |
| `prepare` | `prep` | collectstatic + update_index + restart_uwsgi |
| `test` | -- | Run Django tests (with optional coverage) |
| `server` | -- | runserver (dev only) |

### Elasticsearch (`es.*`)
| Task | Alias | Description |
|------|-------|-------------|
| `es.update_license` | `es.ul` | Update ES X-Pack license (basic/commercial) |

## Patterns

### Task discovery

Collections are assembled in `__init__.py`:
```python
ns = Collection()
ns.add_task(setup_site)
ns.add_collection(borg)
ns.add_collection(Collection.from_module(database, "db"))
ns.add_collection(Collection.from_module(es, "es"))
```

### The `dj()` helper

All Django management commands are invoked through `dj()` in `utils.py`:
```python
def dj(ctx, command, **kwargs):
    ctx.run(
        "{python} manage.py {dj_command} --settings {project_conf}".format(
            dj_command=command, **env
        ), **kwargs,
    )
```

### Borg restore flow

```
borg.restore_database(ctx, repo, archive)
  -> get_latest_borg_backup_archive_name()  # if no archive specified
  -> _extract(ctx, repo, archive, ["backups"])
  -> _restore_database(ctx, working_directory, target_database)
     -> db.restore_from_dump(ctx, dumpfile=..., force=True, migrate=False)
        -> db.drop(ctx, create=True)
        -> zcat dump.sql.gz | psql ...
```

### Confirmation guards

Destructive tasks use `core.utils.confirm()` which prompts for `y/n` input. This is why AI agents cannot safely run these.

## Gotchas

- **`docker-compose.yml` is generated**, never hand-edited. It is built by `config/docker/dc.build.sh` from `base.yml` + environment overlays (`dev.yml`, `staging.yml`, `prod.yml`).
- **Tasks run inside the container.** They assume Django settings and PostgreSQL are available. Running them on the host will fail.
- **Borg environment variables:** `BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK` and `BORG_RELOCATED_REPO_ACCESS_IS_OK` are set automatically in `borg.py:environment()`.
- **`drupal.py` is legacy.** Used for one-time migration from the old Drupal site. Not relevant for current development.
