# Borg replication: infrastructure-owned backup-host pull

Updated 2026-10-23. This replaces the application push design and the earlier pull
proposal. The current authority is infrastructure
[ADR 0038](https://github.com/comses/infrastructure/blob/main/docs/decisions/0038-backup-host-owned-borg-pull.md).
Application push code, tests, secret declarations and placeholder creation have
been removed. No push compatibility interface is retained.

## Application contract

The application owns PostgreSQL dump capture, selected library/media/repository
files, local Borg archives and integrity checks, and the atomic
`last-successful-backup` marker. Backup, explicit prune/compact and restores keep
using the existing `.backup.lock`. Their behavior and archive layout are unchanged.

On deployed hosts, `/srv/backups/comses` is bound to
`/srv/apps/comses/docker/shared/backups` and mounted at `/shared/backups` in the
server. Infrastructure reads `/srv/backups/comses/repo` and the adjacent marker.
The host and container must observe the same application lock inode; do not
replace these directories or the lock pathname during an operation.

Infrastructure installs its own pinned Borg 1.4.5 host runtime. The container's
Borg installation remains responsible for local operations. No application export
task, Docker access for the SSH caller, container rsync dependency, destination SSH
private key or cloud credential is required.

## Pull ownership and safeguards

- The backup host generates and retains its source-read private key. The source
  authorizes its public key through infrastructure's root-controlled broker,
  restricted to fixed status and validated sender commands. The exporter holds
  both the application flock and Borg repository lock throughout export and
  rejects a changed admission token. The sender runs as the repository owner;
  command restrictions are not a read-only filesystem sandbox.
- The source must have no destination-write identity or snapshot credential.
  Infrastructure owns authorization, credential retirement and host runtime
  deployment; application code does not manage those authorities.
- The backup host owns polling/admission, the destination lock, exact Cinder mount
  checks, pre-transfer snapshots, mirroring with `--delete-delay`, bounded retries
  and attempt/transfer records. Its mirror is `/srv/backups/borg/comses-staging`;
  persistent keys and records live separately under `/srv/backups/state/comses-borg`.
- Transfer, independent integrity verification and fresh-system recovery have
  separate evidence and age signals. A successful copy or pre-transfer snapshot
  does not establish recoverability. Cinder snapshots cover the whole volume,
  including the pull key, and must be protected accordingly. Retention and recovery
  authority remain with the independent operator.
- Prune/compact changes repository contents without updating the application
  backup marker. Infrastructure provides explicit reconciliation of the same
  fresh backup. Never independently prune/compact the mirror or retain obsolete
  segments as a substitute for snapshot history.
- Copied locks and unexpected source supervisor loss require the infrastructure
  recovery procedure. Never automatically break source locks. The active mirror
  is unavailable during transfer and requires independent verification afterward.

## Deployment and acceptance

Regenerate Compose, rebuild and recreate `server` to remove the retired wrapper
and secret mounts from the running application. Existing ignored secret files
are not deleted by this change, and removing mounts does not revoke credentials.
Use infrastructure's source-authority retirement procedure for any remaining
keys or cloud credentials. Do not run old push commands alongside pull.

As recorded in infrastructure on 2026-10-23, the first staging pull completed;
integrity verification, recovery and scheduling acceptance were still outstanding.
This application change does not approve scheduling, perform a live deployment,
or establish production readiness. Application tests cover Compose credential
removal and placeholder generation; infrastructure owns exporter, transport,
snapshot, cancellation and recovery tests.

Operational authorities:

- [Replication specification](https://github.com/comses/infrastructure/blob/main/docs/comses-borg-repository-replication-spec.md).
- [Staging rollout and acceptance](https://github.com/comses/infrastructure/blob/main/docs/comses-borg-staging-rollout.md).
- [Maintenance, verification and recovery](https://github.com/comses/infrastructure/blob/main/docs/comses-borg-maintenance.md).
- Local capture/restore/retention: `docs/agents/backup-restore-runbook.md`.
