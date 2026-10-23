# Deployed storage layout and migration

This runbook is the canonical host-path contract for staging and production.
Development keeps repository-local defaults.

## Infrastructure/application ownership boundary

Two distinct ownership policies apply on deployed hosts:

- **Infrastructure owns the canonical collaborative bind roots** `/srv/logs/comses`
  and `/srv/backups/comses`, plus the checkout paths they are bind-mounted onto
  (`docker/shared/logs` and `docker/shared/backups`). Infrastructure bind-mounts
  each canonical `/srv/*` path onto its checkout counterpart, so both paths
  expose the *same inode*. Infrastructure applies its own collaborative access
  policy to these roots, typically `debian:operators 2775`. The application
  does not require, and must not enforce, one exact owner/group/mode on these
  two roots: `deploy/scripts/storage-preflight` validates them for security and
  functionality instead (existence, no symlinks, correct filesystem, not
  world-writable, effective read/write access, and that the bind target and
  checkout source resolve to the same filesystem object), and
  `deploy/scripts/prepare-host-storage` never chowns or chmods them.
- **The application owns and strictly validates every other private or
  service-specific path** beneath `/srv/apps/comses/docker` — `docker/shared`
  (excluding the `backups` and `logs` subdirectories), `docker/pgdata`,
  `docker/secrets`, Redis state, Elasticsearch primary/secondary state, the
  nginx log subdirectory nested under the collaborative logs root, and other
  application-managed private state. These require an exact numeric
  owner/group/mode because the pinned container images run as fixed UIDs/GIDs
  that need precisely that access, no more and no less.

Logs and backups are collaborative because they are the paths operators need
to read, rotate, ship, or replicate outside of application control (log
shipping, Borg replication, retention). Making them exclusively
application-owned would either lock operators out or force infrastructure to
fight the application over ownership on every deploy; making them
application-private with an exact mode is also physically impossible here,
since the bind mount means `/srv/logs/comses` and `docker/shared/logs` (and
similarly for backups) are the same object, so infrastructure's `debian:operators
2775` and any conflicting application-required exact mode cannot both hold.
The setgid bit and group-writable access for the `operators` group are
therefore expected and accepted; `storage-preflight` still fails closed on
world-writable modes or group-writable access by any group other than the
application, deployment, or operators group.

## Path classification

| Class | Host path | Container path / consumer | Owner and mode | Authority |
|---|---|---|---|---|
| 1. Source-controlled, replaceable | `/srv/apps/comses` excluding `docker/`, `.env`, and generated `docker-compose.yml` | build contexts and read-only configuration binds | deployment user; normal checkout modes | Application (checkout) |
| 2. Durable application state | `/srv/apps/comses/docker/shared/{library,media,repository,data,incoming,.latest}` | `/shared/*`; selected paths are read-only in nginx | `0:0`; directories `0755` | Application (exact) |
| 2. PostgreSQL state | `/srv/apps/comses/docker/pgdata` | db `/var/lib/postgresql/data`; not mounted by server | `999:999`; `0700` | Application (exact) |
| 6. Disposable cache or generated state | `/srv/apps/comses/docker/shared/{redis,elasticsearch,static,vite,statistics,tests,extract,uploads}` | Redis, Elasticsearch, collected assets, exports, tests, and temporary upload/restore data | Redis `999:1000` `0750`; Elasticsearch `1000:0` `0750`; remaining directories `0:0` `0755` | Application (exact) |
| 2. ACME challenge state | `/srv/apps/comses/docker/shared/tls/well-known` | nginx `/srv/.well-known` | `0:0`; `0755` | Application (exact) |
| 3. Durable logs | `/srv/logs/comses`, bind-mounted onto `docker/shared/logs` (same inode) | server/db `/shared/logs`; nginx `/var/log/nginx` mounts the nested `nginx` subdirectory | infrastructure collaborative policy, typically `debian:operators 2775`; not world-writable | **Infrastructure** (collaborative root) |
| 3. nginx log subdirectory | `/srv/logs/comses/nginx` | nginx `/var/log/nginx` | `101:101`; `0750` | Application (exact, nested in an infrastructure root) |
| 4. Backup data | `/srv/backups/comses`, bind-mounted onto `docker/shared/backups` (same inode; Borg `repo`, imports, DB dumps, and preserved clusters) | `/shared/backups`; Borg uses `/shared/backups/repo` | infrastructure collaborative policy, typically `debian:operators 2775`; not world-writable | **Infrastructure** (collaborative root) |
| 5. Secret material | `/srv/apps/comses/docker/secrets` and `/srv/apps/comses/.env` | Compose secrets and runtime environment | deployment user; directory `0700`, files `0600` | Application (exact) |
| 6. Disposable state | Compose `sockets` volume, container writable layers, and Docker-managed service stdout | Unix sockets and runtime scratch data | service-specific; no authoritative data | Application/Docker runtime |

The application-local Borg repository remains `/shared/backups/repo` inside the
server container, backed by `/srv/backups/comses/repo` on deployed hosts.
Infrastructure's source exporter holds `/srv/backups/comses/.backup.lock` (the
same inode as the container's `/shared/backups/.backup.lock`) and the Borg lock
while the backup host pulls into `/srv/backups/borg/comses-staging`.
The backup host retains its pull private key; the application has no replication
key or destination snapshot credential. See `docs/agents/borg-replication-design.md`.

TLS terminates upstream in the current production topology. If certificate private
keys are later stored on this host, place them under the secret root, not
`docker/shared/tls` (which contains only public ACME challenge files).
Application and nginx file logs are bound to `/srv/logs/comses`; PostgreSQL,
Redis, and Elasticsearch currently emit operational diagnostics to container
stdout. Those streams are disposable. If infrastructure retains them, its
Docker logging driver/data root must also use Cinder-backed storage or remote
log transport rather than the host root filesystem.

The UID/GID values match the currently pinned images and are parameters to
`deploy/scripts/prepare-host-storage`. Confirm them after an image change with
`docker run --rm --entrypoint id <image>` before changing infrastructure.

`COMSES_BACKUPS_ROOT` (default `/srv/backups/comses`) names the canonical
backups bind root the same way `COMSES_LOG_ROOT` names the canonical logs bind
root. Neither variable is consumed directly by Compose; Compose binds
`docker/shared` (which contains `backups`) and `COMSES_LOG_ROOT` as today.
`storage-preflight` uses `COMSES_BACKUPS_ROOT` only to confirm the
infrastructure bind mount is in place and resolves to the same filesystem
object as `docker/shared/backups`.

### Volume identity ownership

`comses/infrastructure` provisions the Cinder volumes and owns verification
that the intended volumes are mounted. The application checks that `/srv` is
an exact mountpoint before preparing storage or deploying, that application
paths are not on `/`, and that the collaborative log and backup bind paths
resolve to their canonical sources. These checks detect missing mounts and
unsafe path layout; they do not claim to identify the underlying Cinder volume.

### Accepted export access exception

`curator_statistics` writes per-download rows to `/shared/statistics/downloads.csv`
by default. It replaces authenticated users' database IDs with stable HMAC-SHA-256
`user_token` values and omits full IP addresses. The remaining timestamps,
affiliations, and referrers can still make rows linkable. The existing `0755`
statistics directory and normal file creation mode are accepted for staging
and production because these hosts have no local users beyond trusted operators.
This is an explicit exception to private file modes for this operator export.
Revisit the exception before giving other users or services access to the host
or shared tree.

`make secrets` creates `docker/secrets/download_analytics_hmac_key` once,
under the configured application root in every environment. Keep this separate
32-byte key private and preserve it across rebuilds and restores: replacing it
changes future user tokens and breaks cross-export joins. A missing or malformed
key causes the export to fail.

## Infrastructure preparation

The checkout must already exist at the physical path `/srv/apps/comses`; it
must not be a symlink. Infrastructure is responsible for bind-mounting
`/srv/logs/comses` onto `docker/shared/logs` and `/srv/backups/comses` onto
`docker/shared/backups` before `prepare-host-storage` runs, and for applying
its collaborative ownership policy to those two roots. Verify that
`/srv/apps/comses` and `/srv/logs/comses` resolve to Cinder-backed filesystems
rather than `/`, then run:

```bash
cd /srv/apps/comses
sudo deploy/scripts/prepare-host-storage
make storage-preflight
```

The preparation script is idempotent. It creates and repairs the exact
private/service-owned directories listed above; it never chowns or chmods
`docker/shared/logs`/`/srv/logs/comses` or `docker/shared/backups`/
`/srv/backups/comses` themselves, since infrastructure owns those roots. It
may still create application-owned child paths inside them (e.g.
`docker/shared/backups/repo`) without changing their owner or mode. It does
not recursively traverse the checkout or a durable tree and rejects a symlink
at any managed root.

For staging and production, `config.mk` must resolve these values:

```make
COMSES_APP_ROOT=/srv/apps/comses
COMSES_SHARED_ROOT=/srv/apps/comses/docker/shared
COMSES_POSTGRES_ROOT=/srv/apps/comses/docker/pgdata
COMSES_LOG_ROOT=/srv/logs/comses
COMSES_BACKUPS_ROOT=/srv/backups/comses
COMSES_SECRETS_ROOT=/srv/apps/comses/docker/secrets
```

## In-place migration from the previous layout

Staging and production already use `/srv/apps/comses`. Do not move or copy the
checkout and do not copy the entire `docker/shared` tree: library files, media,
the repository, Redis state, and the Borg repository are already in their final
locations. PostgreSQL remains isolated at `docker/pgdata`; only logs, secrets,
and the nginx ACME challenge path change host locations. Run this procedure
independently on each host, staging first.

Migrating to the shared collaborative ownership policy on an already-migrated
host is an infrastructure-side, in-place ownership change: infrastructure
re-applies `debian:operators 2775` (or leaves its existing equivalent policy)
to `/srv/logs/comses` and `/srv/backups/comses`; no data moves. Re-run
`deploy/scripts/storage-preflight` afterward to confirm the new policy still
passes. If infrastructure needs to roll back to a stricter single-owner mode on
these two roots temporarily, `storage-preflight` still accepts a non-broad,
non-collaborative mode (e.g. `root:root 0755`) on logs/backups, since it only
fails closed on world-writable or unexpectedly broad group access; it does not
require the `operators` group. Rolling back the ownership policy therefore
never requires re-running `prepare-host-storage` or touching application state.

These steps copy rather than move data. The old paths and Elasticsearch named
volumes remain available for rollback. Run each block separately and stop when
a check fails.

1. Preflight the mount, space, sources, symlinks, Compose project, and running
   containers:

   ```bash
   cd /srv/apps/comses
   test "$(pwd -P)" = /srv/apps/comses
   sudo findmnt -T /srv/apps/comses
   sudo findmnt -T /srv
   df -h /srv/apps/comses /srv
   test -f docker/pgdata/PG_VERSION
   test -d docker/shared/logs
   test -f build/secrets/db_password
   sudo find -P docker/pgdata docker/shared/logs build/secrets -type l -print
   docker compose ps
   docker compose -f docker-compose.yml config > build/secrets/compose-before-srv-migration.yml
   chmod 0600 build/secrets/compose-before-srv-migration.yml
   docker volume ls
   ```

   Investigate every listed symlink before continuing; the copy commands must
   not follow it. Record the current Compose project name from `docker compose
   ls` for rollback. Confirm that the saved Compose render contains the current
   `docker/pgdata`, `docker/shared/logs`, `build/secrets`, and Elasticsearch
   named-volume sources before proceeding.

   If `docker/shared/postgres` contains a PostgreSQL cluster, stop and follow
   `docs/agents/postgresql-upgrade-runbook.md` to return it to isolated storage.
   If both secret directories contain different files, stop and identify the
   authoritative copy. The deployment preflight refuses ambiguous secret paths
   until the operator records `COMSES_STORAGE_AUTHORITY=new` after verification.

2. Stop services without deleting their containers, networks, or named
   volumes, then create the new empty destinations:

   ```bash
   docker compose stop
   sudo deploy/scripts/prepare-host-storage
   ```

3. Copy only the paths that change. `-x` stays on the source filesystem and
   `--safe-links` does not follow unsafe operator-created links:

   ```bash
   sudo rsync -aHAXx --numeric-ids --safe-links docker/shared/logs/ /srv/logs/comses/
   sudo rsync -aHAXx --numeric-ids --safe-links build/secrets/ docker/secrets/
   sudo rsync -aHAXx --numeric-ids --safe-links deploy/nginx/well-known/ docker/shared/tls/well-known/
   ```

   The final command copies only existing public ACME challenge material. The
   source-controlled nginx configuration remains in `deploy/nginx`.
   Elasticsearch indexes are deliberately not copied from the old named
   volumes. They are rebuildable class-6 state, and `make deploy` runs
   `inv prepare` to rebuild the index in the new bind mounts.

4. Verify without changing either copy, then repair only the exact managed
   directory owners and modes:

   ```bash
   sudo rsync -aHAXxcni --delete --numeric-ids --safe-links docker/shared/logs/ /srv/logs/comses/
   sudo rsync -aHAXxcni --delete --numeric-ids --safe-links build/secrets/ docker/secrets/
   sudo rsync -aHAXxcni --delete --numeric-ids --safe-links deploy/nginx/well-known/ docker/shared/tls/well-known/
   sudo env COMSES_STORAGE_AUTHORITY=new deploy/scripts/prepare-host-storage
   cmp build/secrets/db_password docker/secrets/db_password
   ```

   The dry runs should emit no differences. Do not recursively `chown` any
   copied tree.

5. Explicitly select the verified destinations, render Compose, recreate the
   services, and validate the mounts and application:

   ```bash
   grep -qxF 'COMSES_STORAGE_AUTHORITY=new' config.mk || printf '\nCOMSES_STORAGE_AUTHORITY=new\n' >> config.mk
   make docker-compose.yml
   make verify-compose-storage
   docker compose up -d --force-recreate
   make verify-container-storage
   docker compose exec -T db pg_isready -U comsesnet -d comsesnet
   docker compose exec -T server ./manage.py check
   ```

   Inspect `docker compose config` and `docker inspect` for every service. All
   durable bind sources must begin with `/srv/apps/comses/docker/shared`,
   `/srv/apps/comses/docker/pgdata`, or `/srv/logs/comses`; source-controlled
   binds must begin with `/srv/apps/comses`.

## Rollback

Do not reverse-copy a database that the new stack has modified. Stop the new
containers and recreate the old configuration using the saved render and the
Compose project name recorded during preflight:

```bash
cd /srv/apps/comses
docker compose stop
docker compose --project-name <recorded-project-name> --project-directory /srv/apps/comses -f docker/secrets/compose-before-srv-migration.yml up -d --force-recreate
```

This remounts the untouched `docker/pgdata`, `docker/shared/logs`, legacy
secrets, and Elasticsearch named volumes. Retain those sources until staging or
production has passed its acceptance and backup-retention period. None of the
migration scripts deletes them automatically.

## Operations after migration

Run deploy, upgrade, maintenance, and rollback commands from
`/srv/apps/comses`. Use `docker compose stop` for brief filesystem maintenance;
reserve `docker compose down` for operations that actually require container or
network removal. Never use recursive `chown` on `/srv/apps/comses`,
`docker/shared`, or `/srv/logs/comses`.
