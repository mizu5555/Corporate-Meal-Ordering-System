"""The approved-vendor list is cached in DB mode and read fresh otherwise.

See `EmployeeOrderingService._approved_vendor_records` and the module-level
`_approved_vendors_cache` in backend/services/employee_ordering_service.py.
"""
from __future__ import annotations

import backend.services.employee_ordering_service as svc_module
from backend.repositories.vendor_profile_repository import VendorRecord
from backend.services.employee_ordering_service import EmployeeOrderingService


class _CountingVendorRepo:
    """Minimal vendor repo whose `list` call count is observable."""

    def __init__(self) -> None:
        self.list_calls = 0

    def list(self, status: str | None = None) -> list[VendorRecord]:
        self.list_calls += 1
        return [VendorRecord(id=1, name="Alice Bento", status="approved")]

    def list_facilities(self, vendor_id: int) -> list:
        return []


def _service(vendor_repo: _CountingVendorRepo) -> EmployeeOrderingService:
    # menu/selection/reporting repos are unused by list_vendors(employee_id=None),
    # so plain stand-ins are enough; reporting is passed explicitly to avoid the
    # default get_reporting_repository() touching the DB during construction.
    return EmployeeOrderingService(
        vendor_repository=vendor_repo,
        menu_item_repository=object(),
        selection_repository=object(),
        audit_log_repository=object(),
        reporting_repository=object(),
    )


def teardown_function() -> None:
    svc_module._approved_vendors_cache.invalidate()


def test_db_mode_caches_approved_vendor_list(monkeypatch) -> None:
    monkeypatch.setattr(svc_module.settings, "database_url", "postgresql://x")
    svc_module._approved_vendors_cache.invalidate()

    repo = _CountingVendorRepo()
    service = _service(repo)

    first = service.list_vendors()
    second = service.list_vendors()

    assert [v.id for v in first] == [1]
    assert [v.id for v in second] == [1]
    # The expensive repo read happened only once despite two list_vendors calls.
    assert repo.list_calls == 1


def test_non_db_mode_does_not_cache(monkeypatch) -> None:
    monkeypatch.setattr(svc_module.settings, "database_url", "")
    svc_module._approved_vendors_cache.invalidate()

    repo = _CountingVendorRepo()
    service = _service(repo)

    service.list_vendors()
    service.list_vendors()

    # In-memory mode reads through every time (read-your-writes for tests).
    assert repo.list_calls == 2


def test_cache_invalidation_forces_refresh(monkeypatch) -> None:
    monkeypatch.setattr(svc_module.settings, "database_url", "postgresql://x")
    svc_module._approved_vendors_cache.invalidate()

    repo = _CountingVendorRepo()
    service = _service(repo)

    service.list_vendors()
    svc_module._approved_vendors_cache.invalidate()
    service.list_vendors()

    assert repo.list_calls == 2
