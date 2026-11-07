from django_redis import get_redis_connection
from huey import RedisHuey
from redis import ConnectionPool
from redis.backoff import NoBackoff
from redis.retry import Retry

from core.redis_policy import CACHE_CONNECT_TIMEOUT, QUEUE_BLOCK_SECONDS, QUEUE_READ_TIMEOUT


class DjangoRedisHuey(RedisHuey):
    """Use the cache endpoint with a separate, bounded queue connection pool."""

    def __init__(self, *args, **kwargs):
        cache_pool = get_redis_connection("default").connection_pool
        options = dict(cache_pool.connection_kwargs)
        options.update(
            socket_connect_timeout=CACHE_CONNECT_TIMEOUT,
            socket_timeout=QUEUE_READ_TIMEOUT,
            retry=Retry(NoBackoff(), 0),
            retry_on_timeout=False,
        )
        kwargs["connection_pool"] = ConnectionPool(
            connection_class=cache_pool.connection_class,
            max_connections=8,
            **options,
        )
        kwargs["read_timeout"] = QUEUE_BLOCK_SECONDS
        super().__init__(*args, **kwargs)
