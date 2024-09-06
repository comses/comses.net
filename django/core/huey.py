from django_redis import get_redis_connection
from huey import RedisHuey


class DjangoRedisHuey(RedisHuey):
    """Huey subclass that uses the existing connection pool
    from the django-redis cache backend
    """

    def __init__(self, *args, **kwargs):
        connection = get_redis_connection("default")
        kwargs["connection_pool"] = connection.connection_pool
        super().__init__(*args, **kwargs)
