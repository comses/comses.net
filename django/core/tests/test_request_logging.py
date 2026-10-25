import asyncio
import io
import json
import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
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
    RequestMetadataHandler,
    RequestMetadataMiddleware,
    configure_request_logging,
    request_context,
)


def fail(request):
    raise ValueError("sensitive exception text")


def forbidden(request):
    return HttpResponse(status=403)


urlpatterns = [path("fail/", fail), path("forbidden/", forbidden)]


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
                "timestamp",
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
            handler = RequestMetadataHandler(active)
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
            "core.request_logging.RequestMetadataHandler",
        )

    def test_timestamp_uses_record_creation_and_duration_is_monotonic(self):
        with (
            patch("logging.time.time", return_value=1609459200.123),
            patch("core.request_logging.perf_counter", side_effect=[10, 10.25]),
        ):
            RequestMetadataMiddleware(lambda request: HttpResponse())(
                self.factory.head("/")
            )
        (record,) = self.records()
        self.assertEqual(record["timestamp"], "2021-01-01T00:00:00.123+00:00")
        self.assertEqual(record["duration_ms"], 250.0)

    @override_settings(
        ROOT_URLCONF=__name__,
        MIDDLEWARE=["core.request_logging.RequestMetadataMiddleware"],
    )
    def test_explicit_error_response_keeps_identity_after_middleware_returns(self):
        edge_id = str(uuid4())
        with self.assertLogs("django.request", level="WARNING") as captured:
            # assertLogs replaces handlers, so attach the configured handler filter.
            logger = logging.getLogger("django.request")
            logger.handlers[0].addFilter(RequestContextFilter())
            response = self.client.get("/forbidden/", HTTP_X_REQUEST_ID=edge_id)
            self.assertEqual(request_context.get(), (None, None))
            logger.warning("unrelated")
        error, unrelated = captured.records
        self.assertEqual(response.status_code, 403)
        self.assertEqual(error.status_code, 403)
        self.assertEqual(error.request_id, edge_id)
        self.assertEqual(error.request_id_source, "incoming")
        self.assertEqual(self.records()[0]["request_id"], error.request_id)
        self.assertEqual(self.records()[0]["status"], 403)
        self.assertIsNone(unrelated.request_id)
        self.assertIsNone(unrelated.request_id_source)

    def test_request_fallback_reads_only_valid_assigned_identity(self):
        class AssignedRequest:
            request_id = str(uuid4())
            request_id_source = "incoming"

            @property
            def META(self):
                raise AssertionError("Raw headers must not be inspected")

        request = AssignedRequest()
        record = logging.LogRecord("core", 20, "", 0, "", (), None)
        record.request = request
        for identity, source, valid in (
            (request.request_id, "incoming", True),
            ("bad\nsecret", "incoming", False),
            (str(uuid4()), "unknown", False),
            (None, None, False),
        ):
            with self.subTest(identity=identity, source=source):
                request.request_id, request.request_id_source = identity, source
                RequestContextFilter().filter(record)
                expected = (identity, source) if valid else (None, None)
                self.assertEqual(
                    (record.request_id, record.request_id_source), expected
                )
        active_id = str(uuid4())
        token = request_context.set((active_id, "incoming"))
        try:
            RequestContextFilter().filter(record)
            self.assertEqual(record.request_id, active_id)
        finally:
            request_context.reset(token)

    def test_handler_failures_preserve_response_exception_and_clear_context(self):
        class FailingStream(io.StringIO):
            def __init__(self, operation):
                super().__init__()
                self.operation = operation

            def write(self, value):
                if self.operation == "write":
                    raise OSError("sensitive write failure")
                return super().write(value)

            def flush(self):
                if self.operation == "flush":
                    raise OSError("sensitive flush failure")
                return super().flush()

        for operation in ("write", "flush", "reopen"):
            for raise_exceptions in (True, False):
                with (
                    self.subTest(
                        operation=operation, raise_exceptions=raise_exceptions
                    ),
                    tempfile.TemporaryDirectory() as directory,
                    patch.object(logging, "raiseExceptions", raise_exceptions),
                    patch("sys.stderr", io.StringIO()) as diagnostic,
                ):
                    active = Path(directory) / "metadata.jsonl"
                    handler = RequestMetadataHandler(active)
                    handler.setFormatter(RequestMetadataFormatter())
                    handler.addFilter(RequestMetadataFilter())
                    self.logger.handlers = [handler]
                    if operation == "reopen":
                        active.rename(active.with_suffix(".1"))
                        reopen = patch.object(
                            handler, "_open", side_effect=OSError("secret reopen")
                        )
                    else:
                        handler.stream.close()
                        handler.stream = FailingStream(operation)
                        # Exercise real StreamHandler.emit write/flush and handleError.
                        reopen = nullcontext()
                    try:
                        with reopen:
                            response = RequestMetadataMiddleware(
                                lambda request: HttpResponse(status=204)
                            )(self.factory.head("/"))
                            self.assertEqual(response.status_code, 204)
                            self.assertEqual(request_context.get(), (None, None))
                            with self.assertRaisesRegex(ValueError, "sensitive"):
                                RequestMetadataMiddleware(fail)(self.factory.head("/"))
                            self.assertEqual(request_context.get(), (None, None))

                            async def view(request):
                                return HttpResponse(status=204)

                            async def async_fail(request):
                                raise ValueError("sensitive exception text")

                            async def run_async_requests():
                                response = await RequestMetadataMiddleware(view)(
                                    self.factory.head("/")
                                )
                                self.assertEqual(response.status_code, 204)
                                self.assertEqual(request_context.get(), (None, None))
                                with self.assertRaisesRegex(ValueError, "sensitive"):
                                    await RequestMetadataMiddleware(async_fail)(
                                        self.factory.head("/")
                                    )
                                self.assertEqual(request_context.get(), (None, None))

                            asyncio.run(run_async_requests())
                        self.assertEqual(
                            diagnostic.getvalue(),
                            "request_metadata_write_failed\n" * 4,
                        )
                    finally:
                        # Disable the injected flush failure for handler cleanup.
                        if isinstance(handler.stream, FailingStream):
                            handler.stream.operation = None
                        handler.close()

    def test_stderr_io_failure_does_not_replace_response_or_exception(self):
        for error in (OSError, ValueError):
            with (
                self.subTest(error=error),
                tempfile.TemporaryDirectory() as directory,
            ):
                active = Path(directory) / "metadata.jsonl"
                handler = RequestMetadataHandler(active)
                handler.setFormatter(RequestMetadataFormatter())
                handler.addFilter(RequestMetadataFilter())
                self.logger.handlers = [handler]
                try:
                    # StreamHandler catches the real flush error and calls handleError.
                    with (
                        patch.object(handler, "flush", side_effect=OSError),
                        patch("sys.stderr.write", side_effect=error),
                    ):
                        response = RequestMetadataMiddleware(
                            lambda request: HttpResponse()
                        )(self.factory.head("/"))
                        self.assertEqual(response.status_code, 200)
                        with self.assertRaisesRegex(ValueError, "sensitive"):
                            RequestMetadataMiddleware(fail)(self.factory.head("/"))
                        self.assertEqual(request_context.get(), (None, None))
                    # A reopen error escapes the handler and is caught by middleware.
                    active.rename(active.with_suffix(".1"))
                    with (
                        patch.object(handler, "_open", side_effect=OSError),
                        patch("sys.stderr.write", side_effect=error),
                    ):
                        response = RequestMetadataMiddleware(
                            lambda request: HttpResponse()
                        )(self.factory.head("/"))
                        self.assertEqual(response.status_code, 200)
                        with self.assertRaisesRegex(ValueError, "sensitive"):
                            RequestMetadataMiddleware(fail)(self.factory.head("/"))
                        self.assertEqual(request_context.get(), (None, None))
                finally:
                    handler.close()
