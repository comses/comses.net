# Redis 7 to Redis 8

Compose now uses `redis:8-alpine` in every environment. Redis 7.x supports a direct
upgrade to Redis 8; no application schema migration is required. Keep the existing
Unix socket, data mount, persistence settings and client dependencies.

Redis contains both Django cache data and the Huey queue. Do not flush it or
discard persistence files during deployment. The local Borg archive does not
include Redis state, so preserve a separate stopped-data copy before upgrading.

## Deployment

Use the canonical checkout and the correct rendered Compose environment. Upgrade
staging first and confirm disk space for a complete copy of Redis data. Record
the currently running Redis image ID for rollback before regenerating Compose,
then pull the new image before starting the maintenance window:

```sh
docker compose images redis
make docker-compose.yml
docker compose pull redis
```

Drain ingress and stop the server so web requests and Huey cannot write while
Redis is persisted. The repository's `make stop` performs the ordered shutdown,
including `SAVE` and graceful termination. Confirm it succeeds before continuing:

```sh
make stop
```

Copy the entire stopped Redis data directory to a separate protected rollback
location, preserving ownership and permissions. The deployed source directory is
`/srv/apps/comses/docker/shared/redis`; check the actual mount before copying.
Include `dump.rdb`, the complete `appendonlydir` and its manifest/segments, and
any legacy AOF files. Do not copy only the RDB: with AOF enabled, Redis loads AOF
on restart. The copy must finish successfully before Redis 8 starts.

Start Redis with the new image and verify it before starting application writers:

```sh
docker compose up -d --no-deps redis
docker compose exec -T redis redis-cli -e -s /data/redis.sock ping
docker compose exec -T redis redis-cli -e -s /data/redis.sock INFO server
docker compose exec -T redis redis-cli -e -s /data/redis.sock INFO persistence
docker compose logs --tail 100 redis
```

Require `PONG`, a `redis_version` beginning with `8.`, and successful persistence
loading without RDB/AOF errors. Confirm existing keys/queue state are present;
PING alone does not prove persistence was loaded. Then resume services using the
normal deployment/startup procedure and check Django cache access and Huey task
processing. Do not enable Redis eviction for this shared cache/queue instance as
part of the version upgrade.

## Rollback

Stop ingress and application workers, then gracefully stop Redis 8. Retain its
data directory for diagnosis. Restore the complete stopped Redis 7 directory copy
with its original ownership and permissions, and use a Compose override selecting
the recorded Redis 7 image ID. Start Redis alone and verify persistence and socket
access before reopening application traffic.

Do not merely change the image tag back against Redis 8 persistence files. Restoring
the pre-upgrade copy discards Redis changes after that copy: reconcile tasks already
executed, newly enqueued, or scheduled during that interval before resuming Huey.

## Isolated verification

Pull `redis:7-alpine` and `redis:8-alpine`, then run from the repository root:

```sh
python3 deploy/tests/test_redis_socket.py
```

The suite checks socket recovery on Redis 8, the image and readiness gate in all
Compose environments, and Redis 7 → 8 → 8 restart with synthetic cache, queued and
scheduled payloads. Both AOF and RDB-only persistence are exercised in disposable
directories with networking disabled and no live application data mounts.

On 2026-10-22, all three tests passed against `redis:8-alpine` resolving to
Redis 8.10.2. Separate disposable-container checks passed Django cache set/get,
`DjangoRedisHuey` enqueue/execute/result retrieval and scheduled-task Lua execution
using the existing application clients. The image retains Redis UID/GID 999:1000.
These checks do not establish that staging or production has been upgraded.

Upstream: [standalone Redis 8 upgrade instructions](https://redis.io/docs/latest/operate/oss_and_stack/install/upgrade/standalone/).
