import configparser
import socket
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.test import SimpleTestCase
from django_redis.cache import RedisCache
from redis.exceptions import ConnectionError, TimeoutError

from core.huey import DjangoRedisHuey
from core.redis_policy import cache_options, QUEUE_BLOCK_SECONDS, QUEUE_READ_TIMEOUT


class DependencyLimitsTests(SimpleTestCase):
    def cache(self, location):
        return RedisCache(location, {"OPTIONS": cache_options()})

    def test_production_worker_ceiling_leaves_database_headroom(self):
        config = configparser.ConfigParser(interpolation=None)
        deploy = Path(__file__).resolve().parents[2] / "deploy"
        config.read([deploy / "uwsgi.ini", deploy / "uwsgi-production.ini"])
        workers = config.getint("uwsgi", "processes")
        threads = config.getint("uwsgi", "threads")
        self.assertLessEqual(workers * threads, 100 - 32)
        for key in ("cheaper", "cheaper-initial", "cheaper-step"):
            self.assertLessEqual(config.getint("uwsgi", key), workers)

    def test_missing_redis_socket_fails_promptly_without_hiding_error(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = self.cache(f"unix://{directory}/missing.sock")
            started = time.monotonic()
            with self.assertRaises(ConnectionError):
                cache.get("unavailable")
            self.assertLess(time.monotonic() - started, 3)
            cache.close()

    def test_unresponsive_redis_has_bounded_wait(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "silent.sock")
            listener = socket.socket(socket.AF_UNIX)
            listener.bind(path)
            listener.listen()
            listener.settimeout(5)
            stop = threading.Event()

            def silent_peer():
                try:
                    connection, _ = listener.accept()
                    with connection:
                        stop.wait(5)
                except OSError:
                    pass

            thread = threading.Thread(target=silent_peer, daemon=True)
            thread.start()
            cache = self.cache("unix://" + path)
            try:
                started = time.monotonic()
                with self.assertRaises((ConnectionError, TimeoutError)):
                    cache.get("unresponsive")
                self.assertLess(time.monotonic() - started, 4)
            finally:
                stop.set()
                listener.close()
                thread.join(timeout=6)
                cache.close()

    def test_queue_pool_does_not_change_cache_timeouts_or_storage_identity(self):
        cache = self.cache(settings.CACHES["default"]["LOCATION"])
        client = cache.client.get_client(write=True)
        with patch("core.huey.get_redis_connection", return_value=client):
            queue = DjangoRedisHuey("dependency-test-" + uuid4().hex)
        pool = queue.storage.pool
        self.assertIsNot(pool, client.connection_pool)
        self.assertEqual(pool.connection_class, client.connection_pool.connection_class)
        self.assertEqual(pool.connection_kwargs["path"], client.connection_pool.connection_kwargs["path"])
        self.assertEqual(client.connection_pool.connection_kwargs["socket_timeout"], 2)
        self.assertEqual(pool.connection_kwargs["socket_timeout"], QUEUE_READ_TIMEOUT)
        self.assertGreater(QUEUE_READ_TIMEOUT, QUEUE_BLOCK_SECONDS)
        try:
            queue.storage.enqueue(b"synthetic-work")
            self.assertEqual(queue.storage.dequeue(), b"synthetic-work")
            started = time.monotonic()
            self.assertIsNone(queue.storage.dequeue())
            self.assertLess(time.monotonic() - started, QUEUE_READ_TIMEOUT)
            key = "dependency-test-" + uuid4().hex
            cache.set(key, "healthy", timeout=10)
            self.assertEqual(cache.get(key), "healthy")
            cache.delete(key)
        finally:
            queue.storage.flush_all()
            pool.disconnect()
            cache.close()
