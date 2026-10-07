import asyncio
import io
import json
import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor
from logging.handlers import WatchedFileHandler
from pathlib import Path
from threading import Barrier
from unittest.mock import patch
from uuid import UUID, uuid4

from django.http import HttpResponse, StreamingHttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import path

from core.request_logging import (
    RequestContextFilter,
    RequestMetadataFilter,
    RequestMetadataFormatter,
    RequestMetadataMiddleware,
    configure_request_logging,
    request_context,
)


def fail(request):
    raise ValueError("sensitive exception text")


urlpatterns = [path("fail/", fail)]


class RequestLoggingTests(SimpleTestCase):
    def setUp(self):
        self.stream = io.StringIO()
        self.handler = logging.StreamHandler(self.stream)
        self.handler.setFormatter(RequestMetadataFormatter())
        self.handler.addFilter(RequestMetadataFilter())
        self.logger = logging.getLogger("request_metadata")
        self.previous = (self.logger.handlers, self.logger.level, self.logger.propagate)
        self.logger.handlers = [self.handler]
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.factory = RequestFactory()

    def tearDown(self):
        self.logger.handlers, self.logger.level, self.logger.propagate = self.previous
        self.assertEqual(request_context.get(), (None, None))

    def records(self):
        return [json.loads(line) for line in self.stream.getvalue().splitlines()]

    def test_edge_id_and_allowlisted_completion(self):
        edge_id = str(uuid4())

        def view(request):
            record = logging.LogRecord("core", 20, "", 0, "secret", (), None)
            RequestContextFilter().filter(record)
            self.assertEqual(record.request_id, edge_id)
            self.assertEqual(request.request_id_source, "incoming")
            return HttpResponse(status=201)

        request = self.factory.head(
            "/secret-file?token=secret",
            HTTP_X_REQUEST_ID=edge_id,
            HTTP_COOKIE="password=secret",
            HTTP_AUTHORIZATION="secret",
        )
        response = RequestMetadataMiddleware(view)(request)
        self.assertEqual(response["X-Request-ID"], edge_id)
        (record,) = self.records()
        self.assertEqual(
            set(record),
            {
                "layer",
                "event",
                "request_id",
                "request_id_source",
                "status",
                "duration_ms",
            },
        )
        self.assertEqual(record["layer"], "django")
        self.assertEqual(record["event"], "request_finished")
        self.assertEqual(record["status"], 201)
        self.assertGreaterEqual(record["duration_ms"], 0)
        self.assertNotIn("secret", self.stream.getvalue())

    def test_fallback_ids(self):
        edge_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        for value, source in [
            (None, "missing"),
            ("", "missing"),
            ("bad\nsecret", "invalid"),
            (edge_id.upper(), "invalid"),
            (str(UUID(int=0)), "invalid"),
            (edge_id + ", " + edge_id, "duplicate"),
            ([edge_id, edge_id], "invalid"),
            (edge_id + "\n", "invalid"),
        ]:
            with self.subTest(value=value):
                request = self.factory.head("/")
                if value is not None:
                    request.META["HTTP_X_REQUEST_ID"] = value
                RequestMetadataMiddleware(lambda request: HttpResponse())(request)
                self.assertEqual(UUID(request.request_id).version, 4)
                self.assertNotEqual(request.request_id, value)
                self.assertEqual(request.request_id_source, "fallback_" + source)

    def test_threads_isolate_context(self):
        barrier = Barrier(2)
        ids = [str(uuid4()), str(uuid4())]

        def view(request):
            barrier.wait(timeout=5)
            self.assertEqual(request_context.get()[0], request.request_id)
            return HttpResponse()

        middleware = RequestMetadataMiddleware(view)

        def run(request_id):
            middleware(self.factory.head("/", HTTP_X_REQUEST_ID=request_id))
            self.assertEqual(request_context.get(), (None, None))

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(run, ids))
        self.assertEqual({record["request_id"] for record in self.records()}, set(ids))

    def test_async_tasks_isolate_context(self):
        async def view(request):
            await asyncio.sleep(0)
            self.assertEqual(request_context.get()[0], request.request_id)
            return HttpResponse()

        middleware = RequestMetadataMiddleware(view)
        ids = [str(uuid4()), str(uuid4())]

        async def run(request_id):
            await middleware(self.factory.head("/", HTTP_X_REQUEST_ID=request_id))
            self.assertEqual(request_context.get(), (None, None))

        async def all_requests():
            await asyncio.gather(*(run(value) for value in ids))

        asyncio.run(all_requests())
        self.assertEqual({record["request_id"] for record in self.records()}, set(ids))

    def test_escaping_exception_is_not_reported_twice(self):
        with self.assertRaisesRegex(ValueError, "sensitive"):
            RequestMetadataMiddleware(fail)(self.factory.head("/"))
        (record,) = self.records()
        self.assertEqual(record["status"], 500)
        self.assertNotIn("sensitive", self.stream.getvalue())

    @override_settings(
        ROOT_URLCONF=__name__,
        MIDDLEWARE=["core.request_logging.RequestMetadataMiddleware"],
    )
    def test_django_converted_exception(self):
        self.client.raise_request_exception = False
        edge_id = str(uuid4())
        with patch("django.core.handlers.exception.log_response"):
            response = self.client.head("/fail/", HTTP_X_REQUEST_ID=edge_id)
        self.assertEqual(response.status_code, 500)
        (record,) = self.records()
        self.assertEqual(record["request_id"], edge_id)
        self.assertEqual(record["status"], 500)

    def test_streaming_completion_is_before_iteration(self):
        def content():
            self.assertEqual(request_context.get(), (None, None))
            yield b"data"

        response = RequestMetadataMiddleware(
            lambda request: StreamingHttpResponse(content())
        )(self.factory.head("/"))
        self.assertEqual(len(self.records()), 1)
        self.assertEqual(b"".join(response.streaming_content), b"data")
        self.assertEqual(len(self.records()), 1)

    def test_messages_and_extras_do_not_enter_metadata(self):
        self.logger.info(
            "secret", extra={"request": "secret", "authorization": "secret"}
        )
        self.logger.info(
            "secret",
            extra={
                "event": "request_finished",
                "request_id": str(uuid4()),
                "request_id_source": ["incoming"],
                "status": 200,
                "duration_ms": 1.0,
            },
        )
        self.assertEqual(self.records(), [])
        self.logger.info(
            "secret",
            extra={
                "event": "request_finished",
                "request_id": str(uuid4()),
                "request_id_source": "incoming",
                "status": 200,
                "duration_ms": 1.0,
                "cookie": "secret",
            },
            exc_info=(ValueError, ValueError("secret"), None),
        )
        self.assertNotIn("secret", self.stream.getvalue())

    def test_watched_handler_reopens_after_rename(self):
        with tempfile.TemporaryDirectory() as directory:
            active = Path(directory) / "request-metadata.jsonl"
            handler = WatchedFileHandler(active)
            try:
                record = logging.LogRecord("probe", 20, "", 0, "before", (), None)
                handler.handle(record)
                archived = active.with_suffix(".1")
                active.rename(archived)
                active.touch(mode=0o640)
                record.msg = "after"
                handler.handle(record)
                self.assertEqual(archived.read_text(), "before\n")
                self.assertEqual(active.read_text(), "after\n")
            finally:
                handler.close()

    def test_metadata_has_one_nonpropagating_handler(self):
        config = {
            "handlers": {"console": {}},
            "formatters": {"verbose": {"format": "%(message)s"}},
            "loggers": {},
        }
        configure_request_logging(config, Path("/tmp"))
        configure_request_logging(config, Path("/tmp"))
        self.assertEqual(config["handlers"]["console"]["filters"], ["request_context"])
        self.assertEqual(
            config["loggers"]["request_metadata"]["handlers"], ["request_metadata"]
        )
        self.assertFalse(config["loggers"]["request_metadata"]["propagate"])
        self.assertEqual(
            config["handlers"]["request_metadata"]["class"],
            "logging.handlers.WatchedFileHandler",
        )

    def test_writer_failure_preserves_response_and_exception(self):
        with (
            patch("core.request_logging.metadata_logger.info", side_effect=OSError),
            patch("sys.stderr", io.StringIO()) as diagnostic,
        ):
            response = RequestMetadataMiddleware(
                lambda request: HttpResponse(status=204)
            )(self.factory.head("/"))
            self.assertEqual(response.status_code, 204)
            with self.assertRaisesRegex(ValueError, "sensitive"):
                RequestMetadataMiddleware(fail)(self.factory.head("/"))
            self.assertNotIn("sensitive", diagnostic.getvalue())
            self.assertIn("request_metadata_write_failed", diagnostic.getvalue())
