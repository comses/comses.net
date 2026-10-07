# Deployment

This project is deployed and run using a multi-container Docker Compose workflow generated from repository config.

## Source of truth

- `make deploy` is the default deployment entrypoint.
- `config.mk` controls the active environment via `DEPLOY_ENVIRONMENT`.
- `docker-compose.yml` is generated from `base.yml` plus environment overlays.
- Makefile Compose commands use the physical checkout path (`pwd -P`) as their
  explicit project directory, including rendering, build, and service commands.
  Existing Compose project-name selection is preserved. Staging and production
  still require the canonical checkout and storage checks; this does not permit
  symlinked deployment storage.

## Environment selection

Set `DEPLOY_ENVIRONMENT` in `config.mk`:

```make
# dev|staging|test|prod
DEPLOY_ENVIRONMENT=dev
```

Supported values:

- `dev`
- `staging`
- `test`
- `prod`

## Configuration and state

- Development runtime config and state remain checkout-relative.
- Staging and production use the canonical checkout `/srv/apps/comses`, durable
  shared state `/srv/apps/comses/docker/shared`, isolated PostgreSQL state
  `/srv/apps/comses/docker/pgdata`, logs `/srv/logs/comses`, and secrets
  `/srv/apps/comses/docker/secrets`. The server container does not mount the
  PostgreSQL data directory.
- The complete writable-path classification, ownership contract, migration,
  rollback, and mount verification procedure is in
  `docs/agents/storage-layout.md`.

## Request metadata logging

Before deploying request-ID instrumentation, follow
`docs/agents/request-metadata-logging.md` for staging rollout, rollback and the
four-layer HEAD probe. Infrastructure must install the companion file rotation
policy and hourly schedule, and writer identities/permissions and reopen behavior
must be verified before enabling the new metadata files. Application deployment
does not install retention rules.

## Standard deployment workflow

From repository root:

```bash
make deploy
```

What `make deploy` does:

1.  Builds and renders `docker-compose.yml` from selected environment files.
2.  Builds images and ensures generated secrets/config files exist.
3.  Pulls base services (and nginx for non-dev environments).
4.  Starts services with Docker Compose.
5.  Runs container preparation via `docker compose exec server inv prepare`.

## Common operational commands

```bash
docker compose logs server
docker compose exec server inv sh
docker compose exec server ./manage.py <command>
```

`db.init` and development container startup apply committed migrations only;
production startup does not generate migration files. Generate new migrations
explicitly during development with `inv db.make-migrations`, review them, and
commit them before deployment.

## Backup and restore

The canonical operational procedure is
`docs/agents/backup-restore-runbook.md`. The summary below covers the common
development workflow.

### Restore with `make restore`

Use `make restore` when you need to rebuild local state from a borg backup bundle.

```bash
make restore
```

What it does:

1.  Runs build prerequisites and ensures generated compose/config artifacts exist.
2.  Uses `build/repo.tar.xz` if present, otherwise downloads it from
    `BORG_REPO_URL` to that path.
3.  Renames any existing `docker/shared/backups/repo` beside the repository with
    a timestamp for safety (remaining on durable storage).
4.  Extracts the selected backup archive into `docker/shared/backups/`.
5.  Starts services and runs `docker compose exec server inv borg.restore`.

Set or update restore source in `config.mk`:

```make
BORG_REPO_URL=https://example.com/repo.tar.xz
```

### General backup workflow

Before risky changes, create a fresh backup of DB + filesystem state from the running stack:

```bash
docker compose exec server inv borg.init borg.backup-all
```

This creates/updates `/shared/backups/repo` in the container. On deployed hosts
that is bind-mounted from `/srv/backups/comses/repo`; in development it remains
`docker/shared/backups/repo`.

`borg.backup-all` holds a non-blocking lock across the complete operation. It
writes a PostgreSQL custom-format dump to a temporary path, validates it with
`pg_restore --list`, and only then promotes it to
`/shared/backups/latest/<database>.dump`. It archives the dump with the library,
media, and repository files, verifies the new archive with `borg check
--verify-data`, and atomically updates `/shared/backups/last-successful-backup`.
Restore verifies the selected archive, restores and migrates the database, and
only then rotates live filesystem content.

Monthly pruning uses the same operation lock and proceeds only when the last
verified local backup is no more than 48 hours old.

### Staging off-host replica interface

The fixed `/code/deploy/comses-borg-replicate` command is available in the
`server` image for infrastructure-managed staging replication. It reads the
existing `/shared/backups/repo`, waits for the same
`/shared/backups/.backup.lock` used by backup and prune, then holds Borg's
repository lock for the entire rsync transfer. It does not schedule runs,
create Cinder snapshots, or write a success marker; infrastructure owns those
steps. This is staging-only and is not a production backup workflow.

The host service must pass these variables with `docker compose exec -T -e`:
`COMSES_BORG_REPLICATION_DESTINATION=borg-replica@backup-01.staging.internal:/`,
`COMSES_BORG_REPLICATION_LOCK_WAIT_SECONDS` (1–3600), and
`COMSES_BORG_EXPECTED_VERSION` (the exact installed Borg version).
`COMSES_BORG_REPOSITORY` may be omitted; if supplied, it must be
`/shared/backups/repo`. `COMSES_BORG_REPLICATION_DELETE` defaults to
`false`; enabling it requires a separately reviewed destination policy and
snapshot rollback test.

Compose mounts `borg_replication_ssh_key` and
`borg_replication_known_hosts` only in `server`, under `/run/secrets/`.
The backing files live in the ignored `docker/secrets/` directory (or the
configured `COMSES_SECRETS_ROOT`). Empty local placeholders are allowed for
Compose rendering, but the wrapper rejects empty or writable files before
network access. Before a staging run, verify that the container has Borg,
rsync, and OpenSSH, the mounted files are nonempty, and the Borg version
matches the supplied value. A nonzero exit means no transfer success should
be recorded; inspect the host service journal and preserve the pre-sync
snapshot. A copied Borg lock may need manual recovery, but run
`borg break-lock` on a replica only after independently confirming no
process is using it.

To package the Borg repository for `make restore`:

```bash
docker compose exec server tar -Jcf /shared/backups/repo.tar.xz -C /shared/backups repo
docker compose cp server:/shared/backups/repo.tar.xz build/repo.tar.xz
```

Publish that bundle at `BORG_REPO_URL`, or retain it at `build/repo.tar.xz` for
a local restore.

If you need to preserve that snapshot while testing another restore:

```bash
mv docker/shared/backups/repo docker/shared/backups/repo.saved
```

Later, move the saved repo back into `docker/shared/backups/repo` and run:

```bash
docker compose exec server inv borg.restore
```

### Safety notes

- Restore operations replace active application state (DB + shared files).
- Monitor the age of `/shared/backups/last-successful-backup`; a stale marker is
  a backup failure even when cron itself is still running.
- Replicate the Borg repository off-host and test a disposable restore regularly.
- Treat restore as destructive to current local state unless you back up first.
- Keep backup/restore operations containerized and run from repository root.

## Notes

- Prefer `docker compose` (plugin) commands, not legacy `docker-compose`.
- Regenerate deployment artifacts by updating `config.mk` and rerunning `make deploy`.
- For a concise command index used by both humans and agents, see `docs/agents/commands.md`.
