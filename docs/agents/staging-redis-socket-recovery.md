# Staging Redis socket recovery — 2026-10-07

Staging Django and Huey could not open `/shared/redis/redis.sock`. Read-only
inspection on `comses-staging` verified:

- The deployed checkout was `68d82c3b`; the physical Compose directory change
  in `07854a4d` was not deployed.
- Existing Redis container `comses-redis-1` was running with `redis:7-alpine`.
- Redis `/data` and Django `/shared/redis` mounted the same host directory,
  `/srv/apps/comses/docker/shared/redis`, with matching directory device/inode.
- The socket pathname was absent on the host and in both containers, while
  Redis's kernel Unix listener still referenced `/data/redis.sock`.
- Redis configuration still used that Unix socket with TCP disabled.

This establishes an unlinked socket pathname, rather than differing mount
directories. It does not establish what removed the socket or attribute the
removal to a deployment change.

With explicit user authorization, ran from `/srv/apps/comses`:

```sh
docker compose restart --timeout 120 redis
```

Verified afterward:

- The Redis container ID and image ID were unchanged.
- Redis socket PING returned `PONG`; the host socket pathname existed again.
- Django's configured default connection (`django_redis.get_redis_connection`)
  returned `True` from PING.
- One Huey consumer process was present; Redis's `evalsha` call counter
  increased from 79 to 84 over five seconds, confirming Lua command activity.
  No task was enqueued as a test.

Only the existing staging Redis container was restarted. No code was deployed,
no production service was changed, and no persistence files were removed.
The new Compose socket health check and server readiness dependency remain
local until deployed. They detect unavailable sockets and gate server startup;
they do not automatically recover a running unhealthy Redis container.

The cause of the unlink remains unresolved. See
[deployment recovery instructions](../source/deployment.md#redis-socket-readiness-and-recovery)
for mount checks and controlled recovery.
