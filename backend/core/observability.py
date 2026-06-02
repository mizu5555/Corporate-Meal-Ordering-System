"""Structured logging + per-request correlation + optional Loki forwarding.

Three colocated concerns, kept in one module so the wiring is easy to follow:

1. `RequestIDMiddleware` — generates a UUID per request, exposes it as the
   `X-Request-ID` response header, and propagates it via a `ContextVar` so any
   log emitted during the request (sync or async, route or service layer)
   picks it up automatically through `RequestIDFilter`.

2. `JsonFormatter` — std-lib only, emits one JSON object per log record with a
   stable field set (`ts`, `level`, `logger`, `msg`, `request_id`, `service`,
   `env`). Any `logger.x(..., extra={...})` extras are merged in. Exceptions
   serialise via `formatException` into a single `exc_info` string field —
   easier to query in Loki than multi-line tracebacks.

3. `configure_logging()` — installs the formatter on root, optionally attaches
   a queue-backed `LokiHandler` when `LOKI_URL` is set. Queue handler keeps the
   request hot path off the network; Loki being unreachable degrades to
   stdout-only without raising. Idempotent so test runs that import `backend.main`
   repeatedly do not stack handlers.

On-demand flame graphs: the backend image bundles `py-spy`. From the deploy host:
    docker exec -it mealorder-staging-backend-1 py-spy record -o /tmp/flame.svg \\
        -d 30 --pid 1
Attach needs `--cap-add SYS_PTRACE` on the container (staging compose adds it).
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import socket
import time
import uuid
from contextvars import ContextVar
from queue import Queue
from typing import Any, Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Default `-` (not empty) makes log lines visibly explicit about "no request
# context" instead of looking like a missing field.
_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

_LOGGING_CONFIGURED = False

# One compact access-log line per request flows to Loki via the root logger.
# Without it the backend emits almost nothing at runtime (uvicorn's own access
# logs use `uvicorn.access`, which does not propagate to root), so Grafana
# Explore stays empty. See issue #183.
_access_logger = logging.getLogger("backend.request")

# Scrape/health endpoints are hit every 15-30s per replica; logging them would
# bury real traffic and bloat Loki. Excluded from the per-request access log.
_ACCESS_LOG_SKIP_PATHS = frozenset({"/health", "/metrics"})

# Container hostname (Docker sets it to the container id). Resolved once at
# import. Exposed per-response as `X-Served-By` so that when the backend runs
# as multiple replicas behind the gateway, you can see which instance served a
# request — direct evidence of load balancing / failover during a demo.
_SERVED_BY = socket.gethostname()

# Fields the JsonFormatter copies from LogRecord. Anything passed via
# `logger.x("...", extra={"key": "value"})` lands as record attributes and is
# captured by the extras pass below.
_RESERVED_LOGRECORD_ATTRS = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "asctime",
        "message",
        "taskName",
        "request_id",
    }
)


class RequestIDFilter(logging.Filter):
    """Inject the current ContextVar request id into every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx.get()
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line. Stable shape, Loki-friendly."""

    def __init__(self, service: str, env: str) -> None:
        super().__init__()
        self._service = service
        self._env = env

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "service": self._service,
            "env": self._env,
        }
        # Merge extras (anything not in the LogRecord standard attribute set).
        for key, value in record.__dict__.items():
            if key in _RESERVED_LOGRECORD_ATTRS or key.startswith("_"):
                continue
            payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Generate a UUID per request, propagate via ContextVar, expose as header.

    Honours an inbound `X-Request-ID` if a client (or upstream proxy like a
    load balancer) already set one — useful for end-to-end correlation across
    services. Falls back to a fresh UUID otherwise.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming = request.headers.get("x-request-id")
        request_id = incoming if incoming else uuid.uuid4().hex
        token = _request_id_ctx.set(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
            # Emit inside the context so RequestIDFilter tags the line with this
            # request's id. Skip scrape/health noise.
            if request.url.path not in _ACCESS_LOG_SKIP_PATHS:
                self._log_access(request, response.status_code, start)
        finally:
            _request_id_ctx.reset(token)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Served-By"] = _SERVED_BY
        return response

    @staticmethod
    def _log_access(request: Request, status_code: int, start: float) -> None:
        """One compact JSON access line per request (fields in body, not labels)."""
        if status_code >= 500:
            level = logging.ERROR
        elif status_code >= 400:
            level = logging.WARNING
        else:
            level = logging.INFO
        _access_logger.log(
            level,
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
            },
        )


def _build_loki_handler(
    loki_url: str, service: str, env: str
) -> logging.Handler | None:
    """Return a queue-backed Loki handler, or None if the optional lib is absent.

    Wrapping `LokiHandler` in `QueueHandler` + `QueueListener` keeps the request
    hot path off the network — log calls return as soon as the record is on the
    in-memory queue. The listener thread drains in the background.

    Loki labels stay narrow (service/env/level) to avoid cardinality blowup.
    Per-record context (request_id, vendor_id, handler) lives inside the JSON
    body, queryable via LogQL `|= "vendor_id=42"` etc.
    """
    try:
        import logging_loki  # type: ignore[import-not-found]
    except ImportError:
        logging.getLogger(__name__).warning(
            "LOKI_URL=%s set but python-logging-loki not installed; "
            "logs stay on stdout",
            loki_url,
        )
        return None

    loki_target = logging_loki.LokiHandler(
        url=f"{loki_url.rstrip('/')}/loki/api/v1/push",
        tags={"service": service, "env": env},
        version="1",
    )
    loki_target.setFormatter(JsonFormatter(service=service, env=env))

    queue: Queue[logging.LogRecord] = Queue(maxsize=10_000)
    queue_handler = logging.handlers.QueueHandler(queue)
    listener = logging.handlers.QueueListener(
        queue, loki_target, respect_handler_level=True
    )
    listener.daemon = True  # type: ignore[attr-defined]
    listener.start()
    return queue_handler


def configure_logging() -> None:
    """Install JSON formatter on root + optional Loki handler. Idempotent."""
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    service = os.getenv("SERVICE_NAME", "mealorder-backend")
    env = os.getenv("APP_ENV", "development")
    loki_url = os.getenv("LOKI_URL", "").strip()

    formatter = JsonFormatter(service=service, env=env)
    request_id_filter = RequestIDFilter()

    stdout_handler = logging.StreamHandler()
    stdout_handler.setFormatter(formatter)
    stdout_handler.addFilter(request_id_filter)

    root = logging.getLogger()
    # Drop any handler installed by basicConfig() / earlier configure pass so
    # we do not double-emit when imports re-run (uvicorn reload, test reload).
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(stdout_handler)
    root.setLevel(logging.INFO)

    if loki_url:
        loki_handler = _build_loki_handler(loki_url, service, env)
        if loki_handler is not None:
            loki_handler.addFilter(request_id_filter)
            root.addHandler(loki_handler)
            logging.getLogger(__name__).info(
                "loki_logging_enabled", extra={"loki_url": loki_url}
            )

    _LOGGING_CONFIGURED = True
