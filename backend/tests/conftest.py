from collections.abc import Generator

import pytest
from prometheus_client import REGISTRY

from backend.core.audit import get_audit_log_repository
from backend.core.employee_identity import get_employee_active_check
from backend.main import app
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.services.employee_ordering_service import _approved_vendors_cache


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
def _clear_approved_vendors_cache() -> Generator[None, None, None]:
    """Reset the process-wide approved-vendor TTL cache around every test.

    The cache is only active in DB mode (``DATABASE_URL`` set), which the
    coverage/integration CI jobs do — without this reset a vendor list cached by
    one test leaks into the next test's fake repo, causing cross-test pollution.
    """
    _approved_vendors_cache.invalidate()
    yield
    _approved_vendors_cache.invalidate()


@pytest.fixture(autouse=True)
def _in_memory_audit_repo() -> Generator[None, None, None]:
    """Unit tests run without a DB — default to the in-memory audit repo so that
    routes that write audit entries don't try to open a Postgres connection."""
    app.dependency_overrides.setdefault(get_audit_log_repository, lambda: AuditLogRepository())
    yield
    app.dependency_overrides.pop(get_audit_log_repository, None)


@pytest.fixture(autouse=True)
def _bypass_employee_active_check(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Unit tests run without a DB — bypass the is_active DB check in require_employee.

    Integration tests (marked with ``pytest.mark.integration``) skip this so
    the real check runs against Postgres.
    """
    if request.node.get_closest_marker("integration"):
        yield
        return
    app.dependency_overrides.setdefault(get_employee_active_check, lambda: (lambda _: None))
    yield
    app.dependency_overrides.pop(get_employee_active_check, None)
