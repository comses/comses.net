# Backup and Restore Runbook

This is the canonical procedure for CoMSES.Net database and shared-file backups
and restores. Run commands from the repository root. Deployed hosts use
`/srv/apps/comses`; development uses the checkout root.

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

The server image installs `/code/deploy/cron.daily/backup`, which invokes
`borg.backup-all` inside the container. The equivalent operator command is:

```bash
docker compose exec -T server inv borg.backup-all
```

Initialize a new local repository once before the first backup:

```bash
docker compose exec -T server inv borg.init
```

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

Do not rsync a Borg repository while backup, check, prune, or compact is
running. Off-host replication must acquire the same `.backup.lock`, copy to a
staging destination, verify the replica, and only then publish it as current.

The staging wrapper mirrors deletions with `--delete-delay`; infrastructure
must take a pre-sync destination snapshot and retain snapshot history
independently. Keeping deleted Borg segments in the active replica can cause
integrity-check failures after source compaction. See
[the replication decision record](borg-replication-design.md) for the
snapshot contract, recovery limits, and alternative designs.

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
verifies and extracts the archive, replaces and migrates the database, and
rotates live shared files. Database-only and files-only restores use the same
lock. Previous live file trees are preserved under `/shared/.latest` during
rotation.

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

## Retention and restore drills

The server image schedules pruning monthly. The task acquires the same lock as
backup and refuses to prune when the local successful-backup marker is missing
or older than 48 hours. Run it manually with:

```bash
docker compose exec -T server inv borg.prune
```

The retention policy keeps 14 daily, 4 weekly, 12 monthly, and all yearly
archives. Review repository growth periodically because yearly retention is
unbounded.

The current task cannot verify off-host replication until that workflow exposes
a replica success marker. Monitor replication separately and do not treat local
prune eligibility as proof that the replica is current.

Periodically restore a selected off-host archive into an explicitly disposable
database and isolated shared root. A successful `borg check` is not a substitute
for a restore drill. Never point a drill at `comsesnet`, `docker/pgdata`, or the
active `/shared` tree.

For PostgreSQL major-version migration and physical-cluster rollback, follow
`docs/agents/postgresql-upgrade-runbook.md`. For host paths, ownership, and
mount invariants, follow `docs/agents/storage-layout.md`.
