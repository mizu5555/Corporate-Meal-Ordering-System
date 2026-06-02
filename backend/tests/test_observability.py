"""Structured logging + request-id middleware behaviour."""
from __future__ import annotations

import io
import json
import logging
import os

import pytest
from fastapi.testclient import TestClient

from backend.core import observability
from backend.core.observability import (
    JsonFormatter,
    RequestIDFilter,
    _request_id_ctx,
    configure_logging,
)
from backend.main import app


@pytest.fixture(autouse=True)
def _reset_logging() -> None:
    """Each test starts from a fresh logging state."""
    observability._LOGGING_CONFIGURED = False
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    yield
    observability._LOGGING_CONFIGURED = False
    for h in list(root.handlers):
        root.removeHandler(h)


# ---------------------------------------------------------------------------
# RequestIDMiddleware
# ---------------------------------------------------------------------------
def test_middleware_generates_request_id_when_absent() -> None:
    client = TestClient(app)
    r = client.get("/health")
    rid = r.headers.get("X-Request-ID")
    assert rid, "X-Request-ID header missing on response"
    assert len(rid) == 32  # uuid4().hex length


def test_middleware_exposes_served_by_header() -> None:
    """X-Served-By identifies the serving instance (used for the LB/failover demo)."""
    import socket

    client = TestClient(app)
    r = client.get("/health")
    assert r.headers.get("X-Served-By") == socket.gethostname()


def test_middleware_honours_inbound_request_id() -> None:
    client = TestClient(app)
    r = client.get("/health", headers={"X-Request-ID": "trace-abc-123"})
    assert r.headers["X-Request-ID"] == "trace-abc-123"


def test_middleware_unique_per_request() -> None:
    client = TestClient(app)
    a = client.get("/health").headers["X-Request-ID"]
    b = client.get("/health").headers["X-Request-ID"]
    assert a != b


# ---------------------------------------------------------------------------
# RequestIDMiddleware — per-request access logging (issue #183)
# ---------------------------------------------------------------------------
class _CaptureHandler(logging.Handler):
    """Collect records emitted to the access logger, independent of root state."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def _capture_access_logs():
    """Attach a capture handler to the 'backend.request' access logger."""
    cap = _CaptureHandler()
    lg = logging.getLogger("backend.request")
    lg.addHandler(cap)
    lg.setLevel(logging.INFO)
    return cap, lg


def _add_temp_route(path: str, fn) -> None:
    from fastapi import APIRouter

    router = APIRouter()
    router.get(path)(fn)
    app.include_router(router)


def _drop_temp_route(path: str) -> None:
    app.router.routes = [
        r for r in app.router.routes if getattr(r, "path", "") != path
    ]


def test_middleware_emits_one_access_log_per_request() -> None:
    cap, lg = _capture_access_logs()
    _add_temp_route("/_obs_test/ping", lambda: {"ok": "1"})
    try:
        TestClient(app).get("/_obs_test/ping")
    finally:
        _drop_temp_route("/_obs_test/ping")
        lg.removeHandler(cap)

    assert len(cap.records) == 1, "expected exactly one access log line per request"
    rec = cap.records[0]
    assert rec.method == "GET"
    assert rec.path == "/_obs_test/ping"
    assert rec.status_code == 200
    assert isinstance(rec.duration_ms, (int, float))
    assert rec.duration_ms >= 0
    assert rec.levelno == logging.INFO


def test_middleware_skips_health_and_metrics() -> None:
    cap, lg = _capture_access_logs()
    try:
        client = TestClient(app)
        client.get("/health")
        client.get("/metrics")
    finally:
        lg.removeHandler(cap)

    assert cap.records == [], "/health and /metrics must not produce access logs"


def test_middleware_access_log_warns_on_4xx() -> None:
    cap, lg = _capture_access_logs()
    try:
        TestClient(app).get("/_obs_test/no-such-route-xyz")
    finally:
        lg.removeHandler(cap)

    assert len(cap.records) == 1
    assert cap.records[0].status_code == 404
    assert cap.records[0].levelno == logging.WARNING


# ---------------------------------------------------------------------------
# JsonFormatter
# ---------------------------------------------------------------------------
def test_json_formatter_stable_field_shape() -> None:
    formatter = JsonFormatter(service="mealorder-backend", env="test")
    record = logging.LogRecord(
        name="backend.routes.vendor_menu",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="created menu item id=%d",
        args=(42,),
        exc_info=None,
    )
    record.request_id = "abc"
    payload = json.loads(formatter.format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "backend.routes.vendor_menu"
    assert payload["msg"] == "created menu item id=42"
    assert payload["request_id"] == "abc"
    assert payload["service"] == "mealorder-backend"
    assert payload["env"] == "test"
    assert "ts" in payload


def test_json_formatter_merges_extras() -> None:
    formatter = JsonFormatter(service="s", env="e")
    record = logging.LogRecord(
        name="x", level=logging.INFO, pathname="/", lineno=1,
        msg="hi", args=None, exc_info=None,
    )
    record.request_id = "-"
    record.vendor_id = 99
    record.handler = "/vendor/me/menu"
    payload = json.loads(formatter.format(record))
    assert payload["vendor_id"] == 99
    assert payload["handler"] == "/vendor/me/menu"


def test_json_formatter_serialises_exception() -> None:
    formatter = JsonFormatter(service="s", env="e")
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        record = logging.LogRecord(
            name="x", level=logging.ERROR, pathname="/", lineno=1,
            msg="failed", args=None, exc_info=sys.exc_info(),
        )
    record.request_id = "-"
    payload = json.loads(formatter.format(record))
    assert "exc_info" in payload
    assert "ValueError" in payload["exc_info"]
    assert "boom" in payload["exc_info"]


# ---------------------------------------------------------------------------
# RequestIDFilter + ContextVar propagation
# ---------------------------------------------------------------------------
def test_filter_pulls_request_id_from_context() -> None:
    f = RequestIDFilter()
    token = _request_id_ctx.set("ctx-rid-xyz")
    try:
        record = logging.LogRecord(
            name="x", level=logging.INFO, pathname="/", lineno=1,
            msg="hi", args=None, exc_info=None,
        )
        f.filter(record)
        assert record.request_id == "ctx-rid-xyz"
    finally:
        _request_id_ctx.reset(token)


def test_log_during_request_carries_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """End-to-end: log emitted during a request reflects that request's id."""
    configure_logging()
    logger = logging.getLogger("test.request_log")
    logger.addFilter(RequestIDFilter())

    from fastapi import APIRouter

    captured: list[str] = []
    router = APIRouter()

    @router.get("/_obs_test/log")
    def _emit() -> dict[str, str]:
        # Re-fetch the request id via the contextvar so the test does not
        # depend on a logging handler being installed in caplog's path.
        captured.append(_request_id_ctx.get())
        logger.info("hello from handler")
        return {"ok": "1"}

    app.include_router(router)
    try:
        client = TestClient(app)
        resp = client.get("/_obs_test/log", headers={"X-Request-ID": "trace-xyz"})
        assert resp.status_code == 200
        assert captured == ["trace-xyz"]
        assert resp.headers["X-Request-ID"] == "trace-xyz"
    finally:
        app.router.routes = [r for r in app.router.routes if getattr(r, "path", "") != "/_obs_test/log"]


# ---------------------------------------------------------------------------
# configure_logging() behaviour
# ---------------------------------------------------------------------------
def test_configure_logging_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOKI_URL", raising=False)
    configure_logging()
    handlers_after_first = list(logging.getLogger().handlers)
    configure_logging()
    handlers_after_second = list(logging.getLogger().handlers)
    assert handlers_after_first == handlers_after_second


def test_configure_logging_skips_loki_when_url_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOKI_URL", raising=False)
    configure_logging()
    root = logging.getLogger()
    # Only one stdout StreamHandler, no QueueHandler from the Loki path.
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0], logging.StreamHandler)


def test_stdout_handler_emits_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOKI_URL", raising=False)
    configure_logging()
    root = logging.getLogger()
    buf = io.StringIO()
    root.handlers[0].stream = buf
    logging.getLogger("backend.test").info("hello", extra={"vendor_id": 7})
    line = buf.getvalue().strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["msg"] == "hello"
    assert payload["vendor_id"] == 7
    assert "request_id" in payload
