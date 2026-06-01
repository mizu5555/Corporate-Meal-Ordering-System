from collections.abc import Generator

import pytest
from prometheus_client import REGISTRY

from backend.core.audit import get_audit_log_repository
from backend.main import app
from backend.repositories.audit_log_repository import AuditLogRepository


def _unregister_inprogress() -> None:
    """Remove the http_requests_inprogress collector so it can be re-registered."""
    for collector in list(REGISTRY._collector_to_names):
        names = REGISTRY._collector_to_names.get(collector, set())
        if "http_requests_inprogress" in names:
            REGISTRY.unregister(collector)


@pytest.fixture(autouse=True)
def _isolate_prometheus_registry() -> Generator[None, None, None]:
    """Prevent registry pollution from importlib.reload(backend.main) in test_root_path."""
    _unregister_inprogress()
    yield
    _unregister_inprogress()


@pytest.fixture(autouse=True)
def _in_memory_audit_repo() -> Generator[None, None, None]:
    """Unit tests run without a DB — default to the in-memory audit repo so that
    routes that write audit entries don't try to open a Postgres connection."""
    app.dependency_overrides.setdefault(get_audit_log_repository, lambda: AuditLogRepository())
    yield
    app.dependency_overrides.pop(get_audit_log_repository, None)
