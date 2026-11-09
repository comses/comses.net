# Archive download and extraction limits

The model library applies the same per-archive budgets to uploaded ZIP/tar/RAR
extraction and imported GitHub ZIP packages. Downloads use a fixed local
`release.zip` filename; remote filename headers and Git tags never determine a
local path. Downloads are staged on the destination filesystem and atomically
replace that file only after a successful, bounded transfer and ZIP signature
check. Failed downloads remove temporary files and preserve the previous archive.
Other existing original files are retained.

## Defaults and policy alignment

| Environment variable / Django setting | Default |
| --- | --- |
| `ARCHIVE_MAX_INPUT_BYTES` | 104857600 (100 MiB) |
| `ARCHIVE_MAX_FILE_BYTES` | 104857600 (100 MiB) |
| `ARCHIVE_MAX_TOTAL_BYTES` | 2147483648 (2 GiB) |
| `ARCHIVE_MAX_MEMBERS` | 10000 |
| `ARCHIVE_MAX_PATH_DEPTH` | 32 components, including the filename |
| `ARCHIVE_MAX_SECONDS` | 45 seconds per download or extraction |

All values must be positive integers. Zero does not disable a limit; it rejects
archive processing. Invalid integer values prevent settings from loading.
Configure overrides in the deployment `.env` and follow the standard
[deployment workflow](../source/deployment.md) to regenerate Compose configuration
and recreate the server container so both web and Huey receive the changes.
A process restart alone does not load changed container environment variables.
Defaults are in `django/core/settings/defaults.py`; the environment template is
`deploy/conf/.env.template`. Updating the template does not update an existing `.env`.

The existing production/staging Nginx limit is 100 MiB **per request**, including
multipart overhead. A browser-uploaded file must therefore be slightly smaller.
The archive input cap also protects direct application calls and remote downloads
that bypass that proxy limit. The individual extracted-file default matches
`GITHUB_INDIVIDUAL_FILE_SIZE_LIMIT` (100 MiB); coordinate overrides rather than
raising one independently. Django's 100 MiB `FILE_UPLOAD_MAX_MEMORY_SIZE` is a
memory-to-disk threshold, not an upload ceiling. Existing editor guidance to use
external data repositories for datasets over 1 GB is guidance, not an enforced
upload allowance.

These are archive-processing limits, not a new per-release storage quota or a
general validator for individually uploaded non-archive files. Increasing the
archive input limit does not increase Nginx's request limit. The RAR checks apply
when the RAR extraction path is reached; this change does not fix the existing
RAR MIME-routing or external-decompressor compatibility issues.

## Operator verification and rejected submissions

After deployment, inspect only the relevant settings without printing secrets:

```sh
docker compose exec -T server ./manage.py shell -c 'from django.conf import settings; print({name: getattr(settings, name) for name in ("ARCHIVE_MAX_INPUT_BYTES", "ARCHIVE_MAX_FILE_BYTES", "ARCHIVE_MAX_TOTAL_BYTES", "ARCHIVE_MAX_MEMBERS", "ARCHIVE_MAX_PATH_DEPTH", "ARCHIVE_MAX_SECONDS", "GITHUB_INDIVIDUAL_FILE_SIZE_LIMIT")})'
```

This checks settings in a fresh process in the running container. Confirm that
both web and Huey were restarted/recreated by the deployment; this command does
not inspect their already-loaded Python settings.

For a rejection:

1. Distinguish a proxy HTTP 413 (the full upload request exceeds 100 MiB) from an
   application archive-limit error. Archive errors identify the violated budget;
   size/count/depth errors include the configured threshold.
2. Ask the submitter to remove unnecessary generated files, reduce directory
   nesting, or place large datasets in an external repository with a persistent
   reference. Splitting an archive does not waive the per-file or mirroring limits.
3. Repeated extraction attempts will hit the same policy. Raise a limit only after
   reviewing the legitimate submission's needs, available temporary/storage space,
   concurrent workload, and the corresponding proxy/mirroring constraints.
4. Retry an upload or GitHub import after correcting the input or configuration.
   Do not reprocess or modify published archival objects in place. Use an
   unpublished release/new version for changed contents.

Standard ZIP uploads now reject unsafe member paths instead of silently sanitizing
them, and reject symbolic-link entries instead of copying their link-target text.
Archives containing links must be repackaged with regular files and directories.

## Enforcement and failure behavior

- Input size is checked before opening uploaded archives. HTTP downloads enforce
  advertised Content-Length when present and count actual streamed bytes even
  when the header is absent or inaccurate. Connect/read timeouts are 10/15 seconds.
- Every member, including directories and repeated paths, consumes the member
  budget. Declared file sizes consume the total budget even if a later member
  overwrites the same path. Path depth is checked before stripping a ZIP root.
- Declared sizes are checked before extracting files. Bounded reads count actual
  output and reject a chunk before writing it if it exceeds a file or total cap.
  Tar sparse files are subject to the same logical/output byte limits.
- ZIP and RAR share path validation and reject links/special entries. Tar retains
  its strict filter and Python's data filter, including sanitized file modes.
- Uploaded archives extract in temporary storage and are not copied into SIP on
  rejection. Imported ZIPs finish extraction before clearing existing SIP data.
  Transfer from staging into SIP is not an atomic directory transaction.

## Boundaries

The time budget is **cooperative**, checked between members and before/after
stream reads. It cannot interrupt a blocked decoder, library header parser,
filesystem call, or RAR subprocess. HTTP timeouts limit connection/read inactivity;
they are not a hard total request deadline. uWSGI's existing 60-second harakiri
remains separate and does not protect Huey tasks.

Archive libraries may parse metadata before the member budget can be checked.
These checks therefore do not impose a hard memory or CPU ceiling. Hard execution
limits require an isolated worker/process with enforceable resource limits and
termination. No recursive archive extraction is performed. Limits are per archive,
not per release or account, and concurrent operations multiply disk/memory demand.
Implicit parent directories are not separate members; a deeply nested file can
create multiple directories, bounded by the path-depth cap.
Temporary output and its subsequent SIP copy can coexist; reserve disk accordingly.
Downloads and extraction each receive their own 45-second budget; a complete import
also performs SIP copying and metadata work outside those budgets. The download ZIP
signature check is not a full CRC/member validation; extraction performs those
checks later. A valid ZIP container rejected during extraction can therefore
replace the local downloaded original while leaving the existing SIP intact.

These changes do not scan historical artifacts or establish whether exploitation
occurred. Perform that investigation separately on the backup recovery drill host.

## Regression checks

Run against a disposable development database (the command resets it):

```sh
make test TEST_ARGS="library.tests.test_archive_security library.tests.test_archive_limits"
```

Tests use small overridden limits, generated ZIP/tar archives, and mocked RAR
metadata/streams and HTTP responses. They cover policy boundaries, rejection before
SIP writes, actual byte accounting, cooperative deadlines, untrusted remote names,
and preservation/cleanup on download failures. They do not exercise an external RAR
decoder or a production network transfer.
