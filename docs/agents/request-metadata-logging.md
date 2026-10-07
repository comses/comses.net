# Request metadata logging: staging rollout and infrastructure handoff

Implementation is prepared in this checkout, not deployed. No remote host was
inspected or changed. Live image digests, firewall rules, writer identities,
permissions, installed rotation policy and retention remain to be verified.
Do not enable the new file writers until the prerequisites below are satisfied.

## Inspected configuration and trust boundary

Production uses `deploy/nginx/nginx-haproxy.conf` via `prod.yml`; staging uses
`deploy/nginx/nginx-staging.conf` via `staging.yml`. Both use `nginx:stable`
(a mutable tag). Both mount the checked-in `deploy/nginx/uwsgi_params`.
That file has no request-ID override. The new named uWSGI location explicitly
sets `uwsgi_pass_request_headers on` and overrides `HTTP_X_REQUEST_ID` with
exactly one validated value. This suppresses automatic copies of that header;
other existing header forwarding is preserved. A local uWSGI packet test verifies
this independently of response headers. The accepted value is the incoming edge
UUID, never Nginx's unrelated `$request_id`.

Both Compose files publish `80:80` on all host interfaces. Nginx requires PROXY
protocol, but PROXY protocol is not authentication. `set_real_ip_from` controls
address interpretation, not access. Staging allow/deny lines are commented out.
uWSGI uses a Unix socket in a volume shared with Nginx, with mode 0664; only its
stats port is published, on loopback. Other containers/host users with socket
access are also inside this trust boundary.

The infrastructure catalog assigns application hosts the internal and
administration security groups. `modules/service-environment/main.tf` permits
TCP from the entire tenant subnet in the internal group; `locals.tf` assigns
that group to application hosts. This is broader than HAProxy alone. UUID
validation proves syntax, not provenance. `request_id_source=incoming` means
accepted from the incoming header, not authenticated as HAProxy. Record and
verify actual security groups, Docker firewall behavior and host restrictions
with infrastructure before interpreting an incoming ID as an edge ID. This
change makes no network or infrastructure access-policy changes.

## Identity, context and timing

Nginx accepts only lowercase canonical UUIDv4 with an RFC variant (`8`, `9`, `a`
or `b`). Missing, malformed, uppercase, non-v4 and comma-joined duplicate values
map to an empty `request_id` and an empty uWSGI parameter. Direct Django requests
preserve valid canonical IDs; otherwise they get a fresh UUIDv4 labelled
`fallback_missing`, `fallback_invalid`, or `fallback_duplicate` (comma-joined
values). Repeated headers joined by Nginx are rejected, including identical
copies. WSGI cannot reconstruct duplicates if an earlier hop discarded or
replaced them. Nginx rejection becomes `fallback_missing` in Django because it
forwards an empty validated parameter; no rejected raw value is logged.

Middleware runs first, leaving the relative order of all existing middleware
unchanged. It assigns `request.request_id` and `request.request_id_source`,
returns the application ID in `X-Request-ID`, and makes the identity available to
configured application handlers via `RequestContextFilter` and `ContextVar`.
Application text logs gain those two fields; they remain separate from metadata.
Context is reset in `finally`, including errors and logging failures. Sync
threads and async tasks are isolated. Work spawned outside the request lifecycle
must manage its own context; do not retain request objects or copy request
context into independent background jobs.

Django's dedicated, non-propagating `request_metadata` logger has exactly one
file handler. Its filter requires a completion event and its formatter emits
only `layer`, `event`, `request_id`, `request_id_source`, `status`, `duration_ms`.
It ignores message, exception and arbitrary extra data. Application messages and
exception text cannot enter this stream. Existing Django and Sentry exception
reporting remains in place: this middleware reports status, not a second
exception. Django-converted errors and escaping exceptions get status 500;
worker termination/harakiri cannot guarantee a completion event. Failed file
reopen emits only the fixed stderr diagnostic `request_metadata_write_failed`
and does not replace the response or original exception. Monitor that diagnostic
and missing metadata.

`duration_ms` uses a monotonic clock and covers middleware processing through
response creation, including normal template rendering. For streaming responses,
the event occurs before iteration, excludes streaming time and iteration errors,
and request context is already cleared during iteration. It does not prove
body delivery. Nginx `request_time` and `upstream_response_time` are seconds;
upstream fields stay JSON strings to preserve empty/`-` values and comma/colon
separated attempts. Do not parse them as single numbers. Nginx `request_length`
is total request bytes (request line + headers + body), not uploaded-file size.

The combined Nginx access stream is replaced by one metadata stream; native
Nginx errors and existing application/uWSGI logs remain diagnostic streams and
may contain existing sensitive text. Never export them as correlation evidence.
Static responses, cache hits and proxy-generated errors may have no Django event.
The HEAD probe below uses `/`, which falls through `try_files` to Django's Wagtail
home page; require a nonempty upstream status and a Django completion event.
Verify no file/cache has shadowed `/` in the deployed configuration.

## Collection, ownership and rotation prerequisite

No new mounts are necessary:

| Stream | Container file | Host file | Writer |
| --- | --- | --- | --- |
| Nginx | `/var/log/nginx/request-metadata.jsonl` | `/srv/logs/comses/nginx/request-metadata.jsonl` | source config: root master/workers |
| Django | `/shared/logs/request-metadata.jsonl` | `/srv/logs/comses/request-metadata.jsonl` | source Dockerfile and uWSGI: root, no uid drop |

The nginx directory's existing storage contract remains `101:101 0750`; actual
Nginx configuration currently says `user root`. Do not change this directory or
the collaborative log root ownership. Precreate only these files as `0:0 0640`
after verifying live processes agree; require infrastructure review if they do
not. Existing files must be regular, nonsymlink files with these permissions.
Do not truncate existing metadata during installation.

`deploy/logrotate.d/comses-request-metadata` is a companion policy for the
infrastructure repository to install as `/etc/logrotate.d/comses-request-metadata`
with root ownership and mode 0644. Application deployment does not install it.
It is deliberately separate from `deploy/logrotate.d/comsesnet`: that older
rule covers `*.log`, not `.jsonl`, and reloads uWSGI for diagnostic logs. Do not
use that reload for the new Django stream. Audit installed rules for overlapping
patterns before adding this policy. Never rotate Docker's internal files.

The companion uses rename/create (no copytruncate), daily rotation, 50 MiB size
threshold, 14 retained archives, maximum archive age 14 days, delayed compression
and explicit root rotation credentials for the collaborative parent. `maxage`
is evaluated when a rotation occurs; idle streams can retain older archives.
Infrastructure
must install an at-least-hourly logrotate schedule; a daily schedule does not
check the size threshold hourly. Approximate archive budget is 700 MiB per stream
at the threshold, plus the active file and traffic between checks. These are
threshold/count/age bounds, not hard disk caps or guaranteed 14-day history.
Monitor disk space and tune budgets with infrastructure. Policy source alone is
not evidence of installed retention.

Django's `WatchedFileHandler` flushes each emit and reopens when device/inode
changes, before the next emit. Each worker reopens independently. Nginx logging
is unbuffered and requires `nginx -s reopen` after rename/create. The companion's
postrotate uses the fixed canonical Compose directory/file, not a mutable script
from the checkout. Infrastructure should own the installed policy and command.
Local tests verify both mechanisms; verify the actual deployed image and mounts
before activating writers and again after a controlled staging rotation.

## Exact staging rollout (operator execution only; not performed here)

1. Record environment `staging`, application host `comses-staging` (inventory
   `comses_01_staging`), edge `arbutus_staging`, SSH identity/jump path and sudo
   privilege. Record previous application release/image digest, previous Compose
   configuration and both Nginx config files in protected operator storage.
   Before staging new files, create one protected rollback snapshot on the app
   host (these commands intentionally refuse to overwrite an existing snapshot):

   ```sh
   set -e
   cd /srv/apps/comses
   sudo install -d -m 0700 /root/comses-request-metadata-rollback
   sudo test ! -e /root/comses-request-metadata-rollback/compose.yml
   sudo install -m 0600 docker-compose.yml /root/comses-request-metadata-rollback/compose.yml
   sudo install -m 0600 deploy/nginx/nginx-staging.conf /root/comses-request-metadata-rollback/nginx-staging.conf
   SERVER_IMAGE="$(docker inspect --format '{{.Image}}' "$(docker compose ps -q server)")"
   NGINX_IMAGE="$(docker inspect --format '{{.Image}}' "$(docker compose ps -q nginx)")"
   printf 'services:\n  server:\n    image: %s\n  nginx:\n    image: %s\n' "$SERVER_IMAGE" "$NGINX_IMAGE" | sudo tee /root/comses-request-metadata-rollback/images.yml >/dev/null
   sudo chmod 0600 /root/comses-request-metadata-rollback/images.yml
   ```

   Do not print environment or secrets. Confirm infrastructure has installed and
   audited the companion root-owned rule and hourly scheduler. Obtain staging
   execution authorization separately; no production reload is part of this work.
2. On the app host, verify storage, numeric process identities, regular-file
   paths and installed rule. Run from the canonical checkout:

   ```sh
   cd /srv/apps/comses
   make storage-preflight
   docker compose exec -T server id
   docker compose exec -T server ps -eo uid,gid,comm
   docker compose exec -T nginx ps -eo uid,gid,comm
   sudo stat -c '%u:%g %a %n' /srv/logs/comses /srv/logs/comses/nginx /etc/logrotate.d/comses-request-metadata
   sudo logrotate --debug /etc/logrotate.d/comses-request-metadata
   systemctl list-timers --all logrotate.timer
   ```

   Infrastructure must verify the hourly timer/service and `/usr/bin/docker`
   command location/project selection. If processes do not run as root, revise
   both file creation and the installed rule before proceeding. For absent files
   only, after verifying both parent paths are nonsymlinks, precreate:

   ```sh
   sudo python3 - <<'PY'
   import os, stat
   for path in ('/srv/logs/comses/request-metadata.jsonl', '/srv/logs/comses/nginx/request-metadata.jsonl'):
       new = not os.path.lexists(path)
       fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o640) if new else os.open(path, os.O_WRONLY | os.O_NOFOLLOW)
       with os.fdopen(fd, 'a') as stream:
           if new:
               os.fchown(stream.fileno(), 0, 0)
               os.fchmod(stream.fileno(), 0o640)
           value = os.fstat(stream.fileno())
           if not stat.S_ISREG(value.st_mode) or (value.st_uid, value.st_gid, stat.S_IMODE(value.st_mode)) != (0, 0, 0o640):
               raise SystemExit('Metadata file owner/type/mode mismatch')
   PY
   ```

3. Before enabling writers, run the isolated tests on the staging host's exact
   locally available Nginx image digest, after reviewing the test fixture. It
   mounts only a temporary directory, publishes no ports and validates both
   original configurations before substituting a Unix probe listener:

   ```sh
   NGINX_TEST_IMAGE="$(docker inspect --format '{{.Image}}' "$(docker compose ps -q nginx)")" python3 deploy/tests/test_request_metadata_nginx.py
   ```

   Require syntax, duplicate header, uWSGI forwarding and reopen success. Validate
   the Python WatchedFileHandler rename/create test with the server image as part
   of the targeted suite **on disposable database/storage only**:
   `make test TEST_ARGS=core.tests.test_request_logging`. That command resets its
   database; do not run it with the staging database or durable state paths.
   Independently verify the installed Python handler on the staging log mount
   before activating metadata (uses only temporary synthetic files, no database):

   ```sh
   docker compose exec -T server python - <<'PY'
   import logging, tempfile
   from pathlib import Path
   from logging.handlers import WatchedFileHandler
   with tempfile.TemporaryDirectory(dir='/shared/logs') as directory:
       active = Path(directory) / 'probe.jsonl'
       active.touch(mode=0o640)
       handler = WatchedFileHandler(active)
       try:
           record = logging.LogRecord('probe', 20, '', 0, 'before', (), None)
           handler.handle(record)
           old_inode = active.stat().st_ino
           archive = active.with_suffix('.1')
           active.rename(archive)
           active.touch(mode=0o640)
           record.msg = 'after'
           handler.handle(record)
           assert active.stat().st_ino != old_inode
           assert archive.read_text() == 'before\n'
           assert active.read_text() == 'after\n'
       finally:
           handler.close()
   print('watched_file_reopen=ok')
   PY
   ```
4. Stage the reviewed release through the normal versioned checkout/image
   workflow. With `DEPLOY_ENVIRONMENT=staging`, regenerate Compose and build only
   the application image; preserve the old image digest. Validate the mounted
   configuration before activating it:

   ```sh
   cd /srv/apps/comses
   make docker-compose.yml
   docker compose build server
   docker compose exec -T nginx nginx -t
   docker compose up -d --no-deps --force-recreate server
   docker compose exec -T nginx nginx -s reload
   ```

   Do not run `make deploy` for this narrow rollout: it can recreate unrelated
   dependencies and run preparation workflows. If the mounted config inode was
   replaced by checkout, recreate nginx using the same verified image instead
   of assuming the old file bind sees new contents. Inspect the effective mount
   and validate with a one-off container first. No timeout, buffering, upload
   limit or harakiri settings change.
5. Run the four-layer probe below. Check expected HTTP/upstream/Django status
   (healthy home page: 200), exactly one record per layer and `incoming` source.
   Record current file inodes and sizes, then force **only the new rule** during
   the authorized staging window:

   ```sh
   sudo stat -c '%i %s %u:%g %a %n' /srv/logs/comses/request-metadata.jsonl /srv/logs/comses/nginx/request-metadata.jsonl
   sudo logrotate --force /etc/logrotate.d/comses-request-metadata
   sudo stat -c '%i %s %u:%g %a %n' /srv/logs/comses/request-metadata.jsonl /srv/logs/comses/nginx/request-metadata.jsonl
   ```

   Repeat the probe with a fresh UUID. Require fresh records in both active
   files, changed active inodes and no growth of the renamed archives after
   reopen settles. Check per-worker file descriptors on the host when traffic
   exercises each worker; an idle Django worker reopens only on its next emit.
   Verify permissions, delayed compression and retained counts on later timer
   runs. A failed Nginx postrotate requires an explicit successful reopen and
   another fresh probe before declaring retention verified.

## Four-layer body-free probe and infrastructure runbook replacement

Use the infrastructure runbook's existing section 3 destinations unchanged.
Replace its pending-adoption paragraph with a link to this runbook. Replace its
app-host Python extraction block with `check-request-metadata` below; this adds
`duration_ms` and `request_id_source` to the allowlist and requires `incoming`.
The following is the exact replacement for the dynamic staging probe.

From the workstation, `ssh arbutus_staging`, then run in Bash on the edge:

```bash
set -o pipefail
REQUEST_ID="$(curl -q --silent --show-error --http1.1 --head --connect-timeout 5 --max-time 20 --resolve staging.comses.net:443:127.0.0.1 -H 'X-Request-ID: 00000000-0000-4000-8000-000000000001' -H 'X-Request-ID: 00000000-0000-4000-8000-000000000002' https://staging.comses.net/ | python3 -c '
import re, sys
blocks = re.split(r"\r?\n\r?\n", sys.stdin.read().strip())
lines = blocks[-1].splitlines()
if not lines or not re.fullmatch(r"HTTP/\S+ [0-9]{3}(?: .*)?", lines[0]):
    sys.exit("No complete HTTP response")
ids = [line.split(":", 1)[1].strip() for line in lines[1:] if line.lower().startswith("x-request-id:")]
if len(ids) != 1 or not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", ids[0]) or ids[0] in ("00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000002"):
    sys.exit("Expected one fresh canonical UUIDv4")
print("probe_http_status=" + lines[0].split()[1], file=sys.stderr)
print(ids[0])
')" && test -n "$REQUEST_ID" && printf 'request_id=%s\n' "$REQUEST_ID" && sudo journalctl -u haproxy --since '5 minutes ago' --grep="request_id=${REQUEST_ID} " --no-pager -o cat
```

Require HAProxy `schema=1 environment=staging method=HEAD`,
`backend=comsesnet_staging server=comsesnet_staging_server`, matching status and
normal termination. TLS verification stays enabled; curl config files are
disabled, no redirects are followed, and no credentials, cookies or bodies are
sent. Only status and ID are printed from response headers. This bypasses
Cloudflare; repeat without `--resolve` for a separate public-path check and
require a fresh HAProxy record before claiming origin coverage.

In a second workstation terminal, `ssh comses-staging`, then:

```sh
cd /srv/apps/comses
printf 'Paste only the generated UUID from the edge probe: '
read -r REQUEST_ID
sudo python3 deploy/scripts/check-request-metadata "$REQUEST_ID"
```

Success requires the same fresh UUID in response, HAProxy journal, Nginx
metadata and Django `request_finished` with `request_id_source=incoming`.
HAProxy overwrites the response header, so that header alone is insufficient.
The two file writers flush each event; there is no configured flush interval to
wait for. A static response, cache hit or proxy error can legitimately lack a
Django record; do not declare full correlation from Nginx alone.

## Exact rollback (authorized staging window only)

Use the protected snapshot created before rollout. The Compose override pins
both recorded image IDs; do not rebuild an old tag and assume it is identical.
Restore configuration **in the existing bound file inode**, then activate the
recorded server image, from `/srv/apps/comses`:

```sh
cd /srv/apps/comses
sudo sh -c 'cat /root/comses-request-metadata-rollback/nginx-staging.conf > /srv/apps/comses/deploy/nginx/nginx-staging.conf'
docker compose exec -T nginx nginx -t
sudo docker compose --project-name comses --project-directory /srv/apps/comses -f /root/comses-request-metadata-rollback/compose.yml -f /root/comses-request-metadata-rollback/images.yml up -d --no-deps --force-recreate server
docker compose exec -T nginx nginx -s reload
```

The catalog's project name is `comses`; verify the actual deployed project label
before using that command and use the recorded label if different. Restore the
previous checkout/Compose source via the normal release workflow afterward so a
future deployment does not re-enable this release. Keep the snapshot protected:
the rendered Compose file can contain sensitive operational settings.

If a file bind still refers to a replaced inode, validate the restored file in a
one-off nginx container and recreate nginx with the recorded image/configuration.
Check the unauthenticated home-page HEAD status and existing diagnostics. Keep
metadata files/archives and installed retention until infrastructure confirms
all new writers have stopped; leaving the rule installed is safe and preserves
existing records. Removing its rule/timer is a separate infrastructure operation,
not achieved by reverting this checkout. Never delete logs or restore Docker
internal logging files during rollback. No database rollback is needed.

## Verification evidence and remaining limits

Local verification on 2026-10-07: 11 targeted Django tests passed via
`make test TEST_ARGS=core.tests.test_request_logging` in a disposable Compose
project with fresh database/shared paths. The cached server image was reused;
only the disposable Makefile skipped image rebuilding. The copied local `.env`
selected Elasticsearch 7.17.28, whose cached image failed in logging initialization.
The disposable stack used cached Elasticsearch 8.15.5 with security disabled and
native logging instead; no repository Elasticsearch configuration was changed.
The source files under test were mounted from the disposable checkout. This
proves the targeted behavior in that runtime, not a freshly built release image.
No migration artifacts were generated in the working checkout.

Both Nginx integration subcases passed. Rotation policy syntax also passed
`logrotate --debug` in an isolated cached server container; files were absent,
so this did not execute postrotate or verify host scheduling. Ruff and
`git diff --check` passed for the changed implementation.

Local Nginx tests validate original syntax with cached `nginx:stable` 1.30.4 and
exercise a temporary Unix listener/uWSGI stub, JSON allowlisting, static/missing
upstream values, malformed/duplicate IDs, 502 records and rename/reopen. They
do not establish the live-host image version, network trust or journal transport.
Upstream lists remain strings by construction; multiple production retry
sequences are not simulated by the single-upstream fixture.

Local Django tests cover incoming/fallback identities, threads/async tasks,
converted/escaping exceptions, completion events, streaming limitations,
sensitive-field omission, sink isolation, file reopen and writer-failure behavior.
No live probe, service reload, production mutation, installed rotation, hourly
scheduling or live retention verification has been performed. Infrastructure
must install/audit the companion policy and schedule, verify trusted routing,
and adopt the runbook command updates before promotion. Production requires a
separate rollout after staging evidence.

References: [Nginx JSON logging](https://nginx.org/en/docs/http/ngx_http_log_module.html),
[Nginx uWSGI header forwarding](https://nginx.org/en/docs/http/ngx_http_uwsgi_module.html#uwsgi_pass_request_headers),
[Python watched files](https://docs.python.org/3/library/logging.handlers.html#watchedfilehandler),
[Django middleware exception conversion](https://docs.djangoproject.com/en/4.2/topics/http/middleware/#exception-handling).
