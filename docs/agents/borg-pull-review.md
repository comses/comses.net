# Borg 1.4.5 and the staging pull design

Review date: 2026-10-22. Scope: the application backup workflow and the planned
backup-staging pull from CoMSES staging. The Borg image upgrade is implemented
here; the pull service and Cinder lifecycle remain infrastructure work. No live
replica or cloud recovery drill was performed by this review.

## Findings

Keep the local archive workflow: validated temporary PostgreSQL dump, atomic dump
promotion, Borg create/check, then atomic successful-backup marker under
`.backup.lock`. Prune/compact and restores share that application lock. This gives
replication a useful serialization boundary without coupling application code to
OpenStack. The nightly online backup still permits database/filesystem skew from
concurrent uploads; use the existing maintenance procedure for a quiescent backup.
`pg_restore --list` validates the dump catalog, not a full database restore.

The current `/code/deploy/comses-borg-replicate` is a push command. It takes the
application lock and `borg with-lock`, then runs rsync with mandatory deletions.
It requires a destination private key in the application container. The adjacent
infrastructure checkout still implements source-side snapshot/transfer orchestration,
a transfer-only marker, and separate operator verification/recovery checkpoints.
Its default expected Borg version is 1.2.8. These are observed code defaults,
not evidence of the currently deployed configuration.

Borg 1.4.5 changes packaging and supplies fixes, but does not provide a native
repository replication command. Its related-repository secrets prepare for Borg 2
transfer; they do not replace rsync in Borg 1.4. Keep the existing repository
format, archive layout, compression, retention and default legacy exit codes.

## Recommended simplifications

1. **One destination-owned job.** Put the timer, destination lock, pre-transfer
   snapshot, rsync receiver, verification and atomic success record on
   backup-staging. Staging needs only a restricted source endpoint. Remove its
   outbound replica key and destination-snapshot credentials after the pull has
   passed acceptance and the old push timer is disabled. Keep cloud authority out
   of the application container; destination service credentials must have only
   the authority needed for their infrastructure task.
2. **One SSH session owns source locking and transfer.** A forced source command
   takes `.backup.lock`, then the Borg repository lock, and runs a restricted
   rsync sender as their child. Both locks remain held until the sender exits,
   including failure/disconnect cleanup. Do not use one SSH call to acquire a lock
   and a second to copy, nor infer safety from a completed-backup marker. A fixed
   host helper can invoke the application container; never grant the SSH account
   unrestricted Docker access, an arbitrary shell, or general sudo commands.
3. **Read-only data authority, narrow lock writes.** The backup host owns its SSH
   private key; staging has only its restricted public key. The source endpoint
   must allow only sending the fixed repository and any explicitly approved
   metadata, rejecting receive mode, alternate paths, forwarding and arbitrary
   commands/options. A packaged `rrsync -ro` under the lock helper is an option
   to validate, avoiding a custom parser of `SSH_ORIGINAL_COMMAND`. Do not evaluate
   that string as shell code. The trusted helper still needs to create lock files;
   a literally read-only repository mount cannot support `borg with-lock`.
   Keep repository payload read-only to the SSH caller, with lock authority held
   by the fixed helper. Here, read-only means the backup host cannot change source
   backup data; the destination must remain writable for the mirror/checks.
4. **One verified-replica record, with attempt records for recovery.** After a
   successful copy and destination check, atomically record source archive and
   archive ID, verification time, pre-transfer snapshot UUID and run ID outside
   the rsync tree. Keep attempt/snapshot identities even on failure. Capture and
   validate the source backup marker under the source lock, and confirm the
   selected archive exists in the destination. Source freshness checked only
   before taking locks leaves a race. A separate transfer-only result can remain
   diagnostic; it must not advance verified health or checkpoint retention.
5. **Same transfer path for normal runs and reconciliation.** A new-archive check
   is a scheduling optimization, not repository-change detection: prune/compact
   do not update the local backup marker. Permit an explicit reconciliation of
   the same fresh archive after retention, interruption, or failed verification.
   Do not rerun destructive source retention to retry a destination copy.

These changes remove the cross-host orchestration and writable destination
credential from the application. They do not require a new backup engine or a
second archive creation pass.

## Destination job contract

1. Acquire the destination lock for the entire operation. All transfer, snapshot,
   verification, retention and recovery entry points must honor it; a lock on
   CoMSES alone does not serialize backup-host operations. Disable the old push
   schedule before enabling pull so the two mechanisms cannot overlap.
2. Verify the destination is the intended mounted Cinder volume and the replica
   directory is dedicated to this mirror. Fail closed on an absent/wrong mount,
   unavailable snapshot quota, or unknown snapshot identity. Quiesce repository
   writers and flush using the established filesystem procedure; create the
   pre-transfer snapshot and wait for its exact volume UUID and `available`
   status before allowing writes. Do not hold source locks while waiting on Cinder.
3. Pull through the single locked source session with bounded lock wait and
   transfer runtime. Preserve the existing mirror deletion policy
   (`--delete-delay`); do not use `--ignore-existing`, retain obsolete segments,
   or independently prune/compact the destination. Transfer failure leaves the
   active mirror unverified and preserves previous tested checkpoints.
4. Once the sender is gone, keep the destination lock and exclude all destination
   Borg users. A source lock copied by rsync requires destination-only lock
   cleanup before verification. `borg break-lock` is acceptable only with proven
   exclusivity; never break the source lock or blindly clear locks on each retry.
   Initially copy locks normally rather than inventing lock-file exclusions.
5. Run full `borg check --verify-data` on the mirror with separate Borg cache and
   security directories. Confirm the selected archive and only then advance the
   verified-replica record. Release source locks after transfer; destination
   verification need not delay the next source backup. Periodic extraction and a
   disposable PostgreSQL restore are still required.
6. Keep snapshot retention separate from transfer success. A pre-transfer
   snapshot is a rollback candidate, not proof of a good backup. Keep the last
   tested recovery checkpoint through failures; promote recovery evidence only
   after restoring a snapshot into a separate volume and testing it. On an
   uncertain snapshot-create outcome, reconcile its UUID/run ID before retrying
   rather than creating duplicates automatically.

Cinder snapshots cover a volume, not just the replica directory. The infrastructure
layout includes other `/srv` data, so a directory lock does not quiesce every
filesystem writer. An attached-volume snapshot alone establishes neither
application consistency nor tested recoverability. Keep the existing backend
quiescence and separate-volume recovery procedure. If filesystem freeze is used,
provide a guaranteed thaw path. Snapshot hold metadata is retention policy, not an
immutable deletion barrier; source/application identities must not control it.

## Changes to defer

- Keep both existing source locks: the application lock covers the complete
  database/archive/marker operation, while Borg's lock also excludes direct Borg
  operations outside Invoke. Removing either makes the protocol harder to prove.
- Keep the current push command and Compose secrets until infrastructure cutover.
  Inverting it opportunistically would break the deployed host command contract.
- Do not add a source Cinder snapshot/clone just to avoid transfer locks. It adds
  another volume lifecycle and source snapshot consistency problem. Consider it
  only if measured transfer time materially blocks nightly backups.
- Do not replace the mirror with two independently written Borg repositories in
  this upgrade. That can improve failure independence and retention, but requires
  consistent prepared inputs, another backup pass and separate keys/caches.
- Do not weaken verification or automatically prune Cinder snapshots to gain
  speed. Measure full-check cost first. `--quick-stats` is optional reporting
  optimization, not a replication or integrity feature.

## Acceptance before pull activation

- Build the image and assert `borg --version` is 1.4.5 under both normal and cron
  PATHs. Update infrastructure's expected-version setting and verifier tooling.
- Run the existing real-tool replication suite on 1.4.5. It covers mirrored
  removals after prune/compact and extracting both current and preserved history;
  it does not test SSH restrictions or Cinder.
- Add infrastructure pull tests proving receive/arbitrary commands and paths are
  denied, source locks remain held throughout the sender, lock contention and
  disconnects fail safely, and a source marker change cannot mislabel a replica.
- Exercise missing/wrong mount, snapshot failure/unknown outcome, interrupted
  transfer, failed destination check, same-archive reconciliation and concurrent
  destination jobs. None may advance verified success or remove a held checkpoint.
- In staging, perform an actual Cinder clone recovery, archive extraction and
  disposable database restore before enabling the timer. Confirm the source
  identity cannot write the mirror or manage its snapshots, and the backup-host
  SSH identity cannot write source repository data.

## References

- Local workflow: `django/curator/invoke_tasks/borg.py`,
  `django/curator/invoke_tasks/database.py`, `django/deploy/comses-borg-replicate`.
- Existing mirror contract: `docs/agents/borg-replication-design.md`.
- Infrastructure files reviewed: `docs/comses-borg-repository-replication-spec.md`,
  `docs/comses-borg-maintenance.md`,
  `docs/decisions/0037-application-owned-backup-infrastructure-checkpoints.md`,
  `ansible/roles/borg_replica_source/files/run-borg-replica` and role defaults
  in the adjacent `comses/infrastructure` checkout. Those files still describe
  push; this review recommends the user's new staging pull direction.
- [Borg upgrade notes and changelog](https://borgbackup.readthedocs.io/en/1.4.5/changes.html).
- [Borg installation dependencies](https://borgbackup.readthedocs.io/en/1.4.5/installation.html#dependencies).
- [Copying repositories](https://borgbackup.readthedocs.io/en/1.4.5/faq.html#can-i-copy-or-synchronize-my-repo-to-another-location).
- [Locks and copied-lock handling](https://borgbackup.readthedocs.io/en/1.4.5/usage/lock.html).
