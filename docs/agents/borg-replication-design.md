# Borg replication: a mirror protected by destination snapshots

Decision date: 2026-10-14. Scope: the existing staging off-host replica.
This records a code change and its operating contract; it does not establish
that a host service, snapshot policy, or live replica has been deployed or tested.

## Decision and reason

Keep the existing local Borg repository and infrastructure-managed off-host
rsync workflow. Make `--delete-delay` mandatory for every transfer. Infrastructure
snapshots preserve older destination states independently of source retention.
The active replica must reflect removals from the source, including segments
removed by `borg compact` after pruning.

Previously, deletion defaulted to false. In an isolated Borg 1.2.8 reproduction,
a first copy followed by another archive, pruning, compaction, and a second copy
returned rsync success but failed `borg check --verify-data` with an index object
count mismatch. Old segments survived alongside the new repository index.
Repeating the mirror with `--delete-delay` removed obsolete files and passed
verification. Retaining those segments is not a supported retention strategy.

The wrapper defaults to deletion and rejects an explicit
`COMSES_BORG_REPLICATION_DELETE=false`, rather than silently overriding an
operator's setting. Omission and `true` are accepted for compatibility. Host
units that pass `false` need updating before activating this version.

## Operating contract and tradeoffs

Infrastructure owns the destination volume, snapshots, scheduling, verification,
and success marker. The application wrapper holds the shared `.backup.lock` and
the source Borg repository lock throughout transfer. It does not create snapshots
or enforce their existence; the host workflow must enforce these prerequisites:

1. Serialize destination snapshots, transfers, verification, and any restore
   operations. Use a dedicated replica tree: the fixed remote endpoint `/` must
   resolve to that tree through the receiver's restriction, not a general host
   filesystem or a directory shared with unrelated files.
2. Confirm snapshot creation completed before writing to the destination. Retain
   the last verified state and keep the pre-sync snapshot on transfer or check
   failure. Snapshotting an already failed transfer does not make it verified.
3. Run the wrapper while holding the existing source locks. Source pruning and
   compaction remain part of local retention; replication propagates their results.
4. After the transfer, verify the destination with `borg check --verify-data`
   before publishing success. A copied source lock remains in the replica;
   remove it only after confirming no process uses the destination. Use a separate
   verification client's Borg cache/security state from the source writer.
5. Exercise snapshot rollback and actual archive extraction before rollout and
   periodically afterward. Recover a historical state into an isolated location
   or restore the dedicated destination volume under the infrastructure procedure.

`--delete-delay` schedules removals for the end of the transfer. It does not make
the entire copy atomic: files may already have changed before a failure, and an
interrupted transfer can leave an inconsistent destination. The pre-sync snapshot
provides the recovery point; readers must not consume the active replica during
transfer. Neither rsync exit zero nor a snapshot alone proves recoverability.

Deletion also propagates accidental source removals or corruption. Snapshot
history supplies an earlier recovery point, subject to its own retention and
verification. Snapshots on the same destination volume do not protect against
loss of that volume or compromise of its snapshot administration. A second
independent backup remains a possible future improvement.

Compaction and changed replica files can increase snapshot storage consumption.
Monitor both active replica and retained snapshot usage; source archive pruning
does not reclaim space still referenced by destination snapshots. Full Borg
verification also adds I/O and elapsed time to the host workflow.

## Alternatives considered

| Implementation | Benefits | Costs and reasons to defer or reject |
| --- | --- | --- |
| Independent local and remote Borg repositories, each populated with `borg create` | Borg's recommended redundancy design; distinct repository IDs and keys; independent retention; source repository damage is not directly mirrored | Two backup operations and separate repository/cache/key management. Both should consume the same prepared database/filesystem inputs when the same recovery point is required. A future option if independence outweighs the existing mirror integration. |
| Copy into a fresh destination generation, verify it, then switch the current pointer | Obsolete files cannot survive from a prior generation; readers can keep using the previous verified generation until promotion | Extra capacity and transfer cost unless the storage supports efficient clones; needs generation cleanup, receiver/path changes, and a safe promotion mechanism. A future option if atomic publication becomes necessary. |
| Clone a verified destination snapshot into a writable generation, mirror with deletions, verify, then promote | Combines an isolated transfer with storage sharing and a previous verified generation | Depends on snapshot/clone support and coordinated volume attachment or path switching. More infrastructure lifecycle work than updating the current mirror. |
| Separate retention of destination volume snapshots around the current mirror | Preserves old repository states while allowing the active mirror to follow source pruning and compaction; fits the existing infrastructure | Selected. Requires enforced pre-sync snapshots, independent snapshot retention, destination isolation, and tested recovery. Transfer itself remains non-atomic. |
| Repeated rsync without deletions | Avoids removing destination files during transfer | Rejected for the active replica: obsolete segments can conflict with current indexes after compaction and storage grows without bound. |
| Prune or compact the copied repository independently | Would appear to provide destination-specific archive retention | Rejected for a continuing mirror: the copy shares the source repository ID and subsequent file synchronization can mix divergent states. Use a separately initialized Borg repository for independent retention. |

## Verification and future changes

`django/deploy/tests/test_borg_replication_wrapper.py` covers default/explicit
deletion, rejection of unsafe configuration, lock waiting, and propagation of
transfer failures. Its real-tool integration case runs the actual wrapper against
temporary local source/destination paths, creates two archives, prunes and compacts
the source, then verifies the mirrored repository and a preserved earlier copy
and extracts their respective payloads for a byte-for-byte comparison.
The earlier copy models snapshot contents; it does not test Cinder snapshot
creation, attachment, rollback, SSH transport, or the restricted remote receiver.
The integration case requires Borg 1.x, rsync, and OpenSSH and otherwise skips.

On 2026-10-14, all seven tests passed with Borg 1.2.8 in the cached
`comses/server:dev` image, using the current wrapper and test files mounted
read-only, no network, and no application data mounts. Both repositories passed
full data verification and their extracted payloads matched the expected bytes.
This validates the wrapper change in the cached runtime, not a rebuilt release
image or live snapshot recovery.

On 2026-10-22, the rebuilt `comses/server:borg-1.4.5` image passed all seven
standalone tests, including the real-tool prune/compact/mirror/extraction case.
Borg resolved through `/usr/local/bin/borg` under normal and cron PATHs; the
application environment passed `pip check`. A separate fixture created by the
cached 1.2.8 image passed `check --verify-data` and extraction in 1.4.5, then
accepted another archive; both old and new payloads extracted correctly.
All repositories were disposable, with network disabled and no application data
mounts. These checks do not validate live SSH restrictions or Cinder recovery.

From the repository root, run in a disposable server container without application
data mounts or network (substitute the appropriate built image tag):

```sh
docker run --rm --network none \
  --mount "type=bind,source=$(pwd)/django/deploy/comses-borg-replicate,target=/code/deploy/comses-borg-replicate,readonly" \
  --mount "type=bind,source=$(pwd)/django/deploy/tests/test_borg_replication_wrapper.py,target=/code/deploy/tests/test_borg_replication_wrapper.py,readonly" \
  --entrypoint python3 comses/server:dev \
  /code/deploy/tests/test_borg_replication_wrapper.py
```

Only the wrapper and its test file are mounted read-only from this checkout. All
test repositories are created under the container's temporary directory. No Django
database setup is needed for this standalone suite. The test uses a directory copy
to model snapshot contents and cannot establish infrastructure snapshot readiness.

Before adopting an alternative, preserve the same acceptance criteria: recoverable
archives after pruning/compaction, stable prepared inputs, serialization of writes,
verified publication of success, and tested recovery from interrupted transfers.
An independent repository additionally needs explicit key/cache management and
its own retention policy.

## Sources

- [Borg 1.2.8 redundant repositories and copying guidance](https://borgbackup.readthedocs.io/en/1.2.8/faq.html#can-i-copy-or-synchronize-my-repo-to-another-location).
- [Borg prune: retention and dry-run guidance](https://borgbackup.readthedocs.io/en/1.2.8/usage/prune.html).
- [Borg compact: reclaiming segment storage](https://borgbackup.readthedocs.io/en/1.2.8/usage/compact.html).
- [Borg with-lock and copied-lock recovery](https://borgbackup.readthedocs.io/en/1.2.8/usage/lock.html).
