"""Bound cache latency independently of Huey's blocking queue reads."""

from redis.backoff import NoBackoff
from redis.retry import Retry

CACHE_CONNECT_TIMEOUT = 1
CACHE_READ_TIMEOUT = 2
QUEUE_READ_TIMEOUT = 10
QUEUE_BLOCK_SECONDS = 1


def cache_options():
    return {
        "CLIENT_CLASS": "django_redis.client.DefaultClient",
        "SOCKET_CONNECT_TIMEOUT": CACHE_CONNECT_TIMEOUT,
        "SOCKET_TIMEOUT": CACHE_READ_TIMEOUT,
        "CONNECTION_POOL_KWARGS": {
            "max_connections": 20,
            "retry": Retry(NoBackoff(), 0),
            "retry_on_timeout": False,
        },
    }
