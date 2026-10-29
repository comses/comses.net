# Backup and Restore Runbook

This is the canonical procedure for CoMSES.Net database and shared-file backups
and restores. Run commands from the repository root. Deployed hosts use
`/srv/apps/comses`; development uses the checkout root.

For host reconstruction from an identified replicated backup, use the
[seed-and-release provisioning workflow](seed-provisioning.md). Infrastructure
delivers the selected working repository and target; this application owns safe
configuration, runtime selection, existing restore/migrations and validation.
Use the same application phases for staging, production rebuilds and drills;
environment authority and activation remain separate. The workflow never selects
the latest archive implicitly or marks infrastructure recovery evidence passed.

## Scope and invariants

Each Borg archive contains:

- a validated PostgreSQL custom-format dump from `/shared/backups/latest`;
- model library files;
- uploaded media;
- the artifact repository.

PostgreSQL physical storage at `docker/pgdata` is not included. Recovery is
performed through `pg_restore`, never by copying a live PostgreSQL data
directory. Do not modify published artifacts in place during recovery.

`borg.backup-all` holds `/shared/backups/.backup.lock`, validates the temporary
dump before promotion, creates and verifies a Borg archive, and then atomically
updates `/shared/backups/last-successful-backup`. A marker is evidence of the
last successful local backup, not evidence of successful off-host replication.

## Routine backup

The server image pins Borg 1.4.5 in `django/requirements.txt`, installs it in the
application virtual environment, and exposes it at `/usr/local/bin/borg`.
Ubuntu's `borgbackup` package is not installed.
The image supports create/check/extract and replication without FUSE; `borg mount`
is not provided by this installation. Use extraction for restore drills.

The server image installs `/code/deploy/cron.daily/backup`, which invokes
`borg.backup-all` inside the container. The equivalent operator command is:

```bash
docker compose exec -T server inv borg.backup-all
```

Initialize a new local repository once before the first backup:

```bash
docker compose exec -T server inv borg.init
```

`inv borg.backup` (alias `borg.b`) also runs this complete workflow. Archive
creation is an internal helper: all public Borg backup commands refresh the dump,
hold the shared lock, verify the archive, and publish the success marker only
after every stage succeeds. A failed dump, archive creation, or verification
leaves the previous success marker unchanged.

Run an on-demand backup with:

```bash
docker compose exec -T server inv borg.backup-all
```

Routine backups run while the application is available. PostgreSQL provides a
consistent database snapshot, but concurrent file uploads can occur on either
side of that snapshot. Before an upgrade or other high-risk operation, use the
maintenance-mode procedure below.

## Maintenance-mode backup

Stop application writers while leaving PostgreSQL available, then run the
backup in a one-off server container:

```bash
docker compose stop server
docker compose run --rm --no-deps server inv borg.backup-all
docker compose up -d server
```

If other services or operator jobs can write shared content, stop them as well.
Do not stop `db` until the dump has completed.

## Verify backup health

Check the success marker, archive inventory, selected archive integrity, and
cron log:

```bash
docker compose exec -T server cat /shared/backups/last-successful-backup
docker compose exec -T server inv borg.list
docker compose exec -T server borg check --verify-data \
  /shared/backups/repo::"<archive-name>"
docker compose exec -T server tail -n 100 /shared/logs/comses-backup.log
```

Treat a missing or stale success marker as a failed backup. Also verify the
off-host replica independently; local Borg verification does not prove that a
replica exists or is current.

### Borg 1.4.5 rollout

Rebuild and recreate the server through the normal deployment procedure, then
check `docker compose exec -T server borg --version` reports `borg 1.4.5`.
Infrastructure installs its own pinned Borg 1.4.5 runtime on source and backup
hosts. It does not use the application executable for replication. Coordinate
host runtime changes through the infrastructure rollout procedure.

For repositories already on 1.2.8 with the earlier TAM security migration
completed, no repository conversion or `borg upgrade` is required. Keep legacy
exit codes (the default); do not enable `BORG_EXIT_CODES=modern` without reviewing
callers. See the upstream
[upgrade notes](https://borgbackup.readthedocs.io/en/1.4.5/changes.html#borg-1-2-x-to-1-4-x).

Before production, exercise a staging backup, infrastructure-managed pull, full
destination check, archive extraction and disposable database restore. Use the
infrastructure replication tests and acceptance procedure linked from
`docs/agents/borg-replication-design.md`; the retired application push suite no
longer applies. Test commands must not mount live application data.

### Replication serialization

Infrastructure's host-side source exporter acquires the same `.backup.lock` and
Borg repository lock throughout the pull. The application keeps its local backup,
marker, prune/compact and restore protocol. No new application export task,
container replication credential, or Cinder interface is required.

The backup host creates a pre-transfer destination snapshot and mirrors deletions
with `--delete-delay`. Readers must not use the active mirror during transfer;
a separate destination check establishes integrity. Transfer, integrity and tested
recovery are distinct records. Source retention still requires explicit maintenance
and subsequent same-backup reconciliation; it does not advance the local backup
marker. Follow `docs/agents/borg-replication-design.md` and the linked infrastructure
procedures for snapshot protection, locking, verification and recovery.

## Select a restore point

List archives and verify the selected archive before any destructive action:

```bash
docker compose exec -T server inv borg.list
docker compose exec -T server borg check --verify-data \
  /shared/backups/repo::"<archive-name>"
```

Record the archive name, current release, database version, and reason for the
restore. Take a maintenance-mode backup of current state unless the current
state is known to be unusable.

## Full restore

This replaces the target database, model library, media, and repository.
Perform it during maintenance mode:

```bash
docker compose stop server
docker compose run --rm --no-deps server inv borg.restore \
  --archive="<archive-name>" --force
docker compose up -d server
```

The restore holds the same `.backup.lock` as backup and prune while it
verifies and extracts the archive, checks its required layout, replaces and
migrates the database, and rotates live shared files. Preflight requires real
library/media directories and a nonempty database dump before replacement begins.
The repository directory may be absent in older archives; if present, it must
also be a real directory. Files-only restores check the directory layout before
rotating any live or previous trees. These checks do not guarantee that every
restore step will succeed or make database/file replacement atomic. Database-only
and files-only restores use the same lock. Previous live file trees are preserved
under `/shared/.latest` during rotation.

If database restore or migration fails, shared files have not yet been rotated.
Leave the application stopped, retain the logs and extracted archive, and
investigate before retrying. If file rotation fails after database replacement,
leave writers stopped and reconcile the database with the current and
`/shared/.latest` file trees before resuming service.

## Database-only restore

This replaces only the database and leaves shared files unchanged. Use it only
when the selected dump is known to correspond to the retained files:

```bash
docker compose stop server
docker compose run --rm --no-deps server inv borg.restore-database \
  --archive="<archive-name>"
docker compose up -d server
```

For a standalone dump already present in the server container:

```bash
docker compose stop server
docker compose run --rm --no-deps server inv db.restore-from-dump \
  --dumpfile="/shared/backups/latest/<database>.dump" --force
docker compose up -d server
```

## Local restore from a packaged repository

`make restore` is intended for rebuilding local state from `build/repo.tar.xz`,
or from `BORG_REPO_URL` when that file is absent:

```bash
make restore
```

It preserves an existing local Borg repository under a timestamped name,
extracts the package into `docker/shared/backups`, starts the stack, and invokes
the full restore. Treat this command as destructive to current local database
and shared-file state.

## Post-restore validation

Do not reopen application traffic until all checks pass:

```bash
docker compose exec -T db pg_isready -U "${DB_USER}" -d "${DB_NAME}"
docker compose exec -T server python manage.py migrate --plan
docker compose exec -T server python manage.py check
make verify-container-storage
```

Also verify representative published releases, file downloads, media, staff
login, search, and background-task processing. Confirm that database records and
stored files correspond to the selected restore point.

## Explicit retention maintenance

The server image does not schedule pruning or compaction. Daily backup creation
and verification remain automatic. Infrastructure owns the coordinated maintenance
procedure, off-host verification, snapshots, retention records, and scheduling.
For staging, follow the [infrastructure maintenance runbook](https://github.com/comses/infrastructure/blob/main/docs/comses-borg-maintenance.md)
before applying local retention. Production requires its own reviewed procedure.

Preview the local retention policy with:

```bash
docker compose exec -T server inv borg.prune
```

This is a dry run and never compacts. After satisfying the infrastructure
maintenance prerequisites, apply from an interactive terminal:

```bash
docker compose exec server inv borg.prune --apply
```

The command repeats the preview and requires confirmation while holding the
shared backup lock, then prunes and compacts under that lock. If pruning fails,
compaction does not start. It refuses retention when the local successful-backup
marker is missing or malformed, its recorded timestamp is older than 24 hours or
in the future, or its named archive is absent from the configured Borg repository.
The timestamp must include a timezone; file modification time is not freshness
evidence. These checks repeat after confirmation, before deletion, so an expired
backup cannot pass on the strength of an earlier preview. The 24-hour limit matches
infrastructure reconciliation admission; allow time for reconciliation or take a
fresh backup before maintenance. Existing markers retain their two-field format.
The marker records completion of the backup's existing data verification; this
gate does not repeat that verification or establish off-host recoverability.
The application does not verify off-host recovery prerequisites or manage cloud
snapshots.

Pruning and compaction change repository files without advancing the local backup
marker. Complete infrastructure reconciliation and destination verification after
applying; never prune or compact the mirrored repository independently. If local
maintenance fails, inspect source integrity before retrying. A later transfer
failure requires reconciliation, not replaying local pruning.

### Configure retention

The defaults keep **14 daily, 8 weekly, 12 monthly, and unlimited yearly** archives.
The values live in `django/core/settings/defaults.py` as `BORG_RETENTION` and
can be overridden with the following settings in the deployment `.env`:

```dotenv
BORG_KEEP_DAILY=14
BORG_KEEP_WEEKLY=8
BORG_KEEP_MONTHLY=12
BORG_KEEP_YEARLY=-1
```

After editing `.env`, regenerate Compose with `make docker-compose.yml` and
recreate the server through the normal deployment procedure. Existing deployments
without these variables use the application defaults. For a one-off preview:

```bash
docker compose exec -T -e BORG_KEEP_WEEKLY=8 -e BORG_KEEP_YEARLY=-1 server inv borg.prune
```

Use the same overrides when applying. Each invocation prints the effective policy
before checking backup freshness, and the preview echoes the exact Borg command.
Counts must be integers: `-1` means unlimited and `0` disables a tier; disabling
all tiers is rejected before accessing the repository.

These are calendar-tier archive counts, not age cutoffs. Borg selects the latest
archive in each period, excluding archives already kept by finer tiers. Unlimited
yearly retention preserves annual representatives indefinitely, not every archive
from each year. Missing periods do not count.
See [Borg pruning semantics](https://borgbackup.readthedocs.io/en/1.4.5/usage/prune.html).

Monitor local storage and repository growth because pruning is explicit and yearly
retention is unbounded. Do not add `--apply` to cron or invoke `borg compact`
separately as routine maintenance.

### Deployment transition

Removing the source cron script does not change an existing container. Rebuild
and recreate the server through the normal deployment procedure, then verify
`/etc/cron.monthly/prune-backups` is absent. If replacing the container must wait,
disable that installed cron entry explicitly before beginning maintenance. Check
that no prune or compaction is already running; removing the schedule does not
stop an existing process.

## Restore drills

Periodically restore a selected off-host archive into an explicitly disposable
database and isolated shared root. A successful `borg check` is not a substitute
for a restore drill. Never point a drill at `comsesnet`, `docker/pgdata`, or the
active `/shared` tree.

For PostgreSQL major-version migration and physical-cluster rollback, follow
`docs/agents/postgresql-upgrade-runbook.md`. For host paths, ownership, and
mount invariants, follow `docs/agents/storage-layout.md`.
