# Production connection budget and Compose ownership

Production loads `django/deploy/uwsgi-production.ini` after the common uWSGI
configuration: at most 16 workers with 4 threads each (64 web request threads).
For a deployment with 100 PostgreSQL connections, this leaves nominal headroom
of 36 for Huey, management commands, maintenance and operators. This is a
concurrency budget, not a database-enforced reservation; overlapping application containers or extra
background workers can still exhaust it. Review the combined budget before
raising any worker count. Monitor request latency and the uWSGI listen backlog:
a lower ceiling trades maximum parallelism for bounded database pressure.

Django cache operations use a 1-second connect timeout and 2-second read timeout,
without automatic retries. Errors remain visible; the application does not
silently treat a Redis outage as a cache miss. These are socket-operation bounds,
not a total request deadline. Huey uses the same endpoint/database and queue
names through a separate pool (8 connections), a 10-second socket timeout and
1-second blocking dequeue. Its longer timeout permits normal idle queue reads
without extending web cache waits. Redis pool limits are per process.

`make deploy` uses the shared [application preflight](deployment-preflight.md)
before building and again against generated Compose configuration before starting
services. It validates storage and candidate bindings, then rejects competing
foreign writers using the same Docker command/context as deployment. Canonical
log/backup aliases are part of the shared storage contract. No conflicting
containers are stopped or deleted automatically.

When changing Compose project names, identify the authoritative containers,
stop obsolete services and disable their restart policies before deploying.
Keep data until its authority and recovery needs are understood. `compose down`
for the new project does not retire the old one. Direct Docker/Compose commands
can bypass this preflight, and it is not a lock against concurrent operators.
Recheck obsolete-container restart policies before host maintenance or reboot.

Administrative connection headroom depends on the runtime database role's
privileges. Use a suitably restricted runtime role and separate migration/admin
credentials; do not assume reserved slots protect against a privileged client.
Keep live incident evidence and host-specific privilege assessments in the
private infrastructure runbook.

Validation: `make test TEST_ARGS=core.tests.test_dependency_limits` exercises
missing/unresponsive Redis, real cache/queue round trips and queue isolation.
Run only against the disposable local test database: this target resets it.
`make test-deploy-contracts` checks deployment ordering, configured Docker
commands, competing mount owners, canonical aliases and restart-policy handling.
