"""Request identity and an allowlisted completion stream, separate from messages."""

import json
import logging
import re
import sys
from contextlib import suppress
from contextvars import ContextVar
from time import perf_counter
from uuid import uuid4

from asgiref.sync import iscoroutinefunction, markcoroutinefunction

UUID4 = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)
request_context = ContextVar("request_context", default=(None, None))
metadata_logger = logging.getLogger("request_metadata")


def request_identity(value):
    if isinstance(value, str) and UUID4.fullmatch(value):
        return value, "incoming"
    source = "fallback_missing" if value in (None, "") else "fallback_invalid"
    if isinstance(value, str) and "," in value:
        source = "fallback_duplicate"
    return str(uuid4()), source


class RequestContextFilter(logging.Filter):
    """Attach identity to application records without retaining request objects."""

    def filter(self, record):
        record.request_id, record.request_id_source = request_context.get()
        return True


class RequestMetadataFilter(logging.Filter):
    def filter(self, record):
        return (
            getattr(record, "event", None) == "request_finished"
            and isinstance(getattr(record, "request_id", None), str)
            and UUID4.fullmatch(record.request_id) is not None
            and getattr(record, "request_id_source", None)
            in (
                "incoming",
                "fallback_missing",
                "fallback_invalid",
                "fallback_duplicate",
            )
            and type(getattr(record, "status", None)) is int
            and type(getattr(record, "duration_ms", None)) is float
        )


class RequestMetadataFormatter(logging.Formatter):
    """Never serialize message, exception, request, or arbitrary extra fields."""

    def format(self, record):
        return json.dumps(
            {
                "layer": "django",
                "event": "request_finished",
                "request_id": record.request_id,
                "request_id_source": record.request_id_source,
                "status": record.status,
                "duration_ms": record.duration_ms,
            },
            allow_nan=False,
            separators=(",", ":"),
        )


class RequestMetadataMiddleware:
    # First in MIDDLEWARE: includes short circuits and Django-converted errors.
    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        self.is_async = iscoroutinefunction(get_response)
        if self.is_async:
            markcoroutinefunction(self)

    def _start(self, request):
        request.request_id, request.request_id_source = request_identity(
            request.META.get("HTTP_X_REQUEST_ID")
        )
        token = request_context.set((request.request_id, request.request_id_source))
        return token, perf_counter()

    def _finish(self, request, status, started, token):
        try:
            metadata_logger.info(
                "",
                extra={
                    "event": "request_finished",
                    "request_id": request.request_id,
                    "request_id_source": request.request_id_source,
                    "status": status,
                    "duration_ms": (perf_counter() - started) * 1000,
                },
            )
        except OSError:
            # A failed reopen must not replace the response or original exception.
            with suppress(OSError):
                print("request_metadata_write_failed", file=sys.stderr)
        finally:
            request_context.reset(token)

    def __call__(self, request):
        if self.is_async:
            return self.__acall__(request)
        token, started = self._start(request)
        status = 500
        try:
            response = self.get_response(request)
            status = response.status_code
            response["X-Request-ID"] = request.request_id
            return response
        finally:
            self._finish(request, status, started, token)

    async def __acall__(self, request):
        token, started = self._start(request)
        status = 500
        try:
            response = await self.get_response(request)
            status = response.status_code
            response["X-Request-ID"] = request.request_id
            return response
        finally:
            self._finish(request, status, started, token)


def configure_request_logging(config, directory):
    """Extend each environment's existing logging config with one file sink."""
    config["filters"] = {
        **config.get("filters", {}),
        "request_context": {"()": RequestContextFilter},
        "request_metadata": {"()": RequestMetadataFilter},
    }
    for handler in config["handlers"].values():
        if "request_context" not in handler.setdefault("filters", []):
            handler["filters"].append("request_context")
    if "%(request_id)s" not in config["formatters"]["verbose"]["format"]:
        config["formatters"]["verbose"]["format"] += (
            " request_id=%(request_id)s request_id_source=%(request_id_source)s"
        )
    config["formatters"]["request_metadata"] = {"()": RequestMetadataFormatter}
    config["handlers"]["request_metadata"] = {
        "class": "logging.handlers.WatchedFileHandler",
        "filename": str(directory / "request-metadata.jsonl"),
        "formatter": "request_metadata",
        "filters": ["request_metadata"],
        "level": "INFO",
    }
    config["loggers"]["request_metadata"] = {
        "handlers": ["request_metadata"],
        "level": "INFO",
        "propagate": False,
    }
