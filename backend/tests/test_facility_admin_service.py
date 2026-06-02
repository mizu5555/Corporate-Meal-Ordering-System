"""Tests for FacilityAdminService — audited facility create/assign."""
from __future__ import annotations

import pytest

from backend.core.errors import CodedHTTPException
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.facility_repository import FacilityRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord
from backend.services.facility_admin_service import FacilityAdminService


def _make_service() -> tuple[FacilityAdminService, FacilityRepository, VendorProfileRepository, AuditLogRepository]:
    facility_repo = FacilityRepository()
    vendor_repo = VendorProfileRepository()
    vendor_repo.seed(VendorRecord(id=1, name="Sunny Kitchen", status="approved"))
    audit_repo = AuditLogRepository()
    svc = FacilityAdminService(
        facility_repository=facility_repo,
        vendor_repository=vendor_repo,
        audit_log_repository=audit_repo,
    )
    return svc, facility_repo, vendor_repo, audit_repo


# ------------------------------------------------------------------
# create_facility
# ------------------------------------------------------------------

def test_create_facility_returns_facility_and_audits() -> None:
    svc, _, _, audit_repo = _make_service()

    facility = svc.create_facility("HQ1", "Headquarters 1", actor_user_id=99, actor_role="admin")

    assert facility.code == "HQ1"
    assert facility.name == "Headquarters 1"
    assert facility.id is not None

    entries = audit_repo.list(action="facility.create")
    assert len(entries) == 1
    entry = entries[0]
    assert entry.target_type == "facility"
    assert entry.target_id == facility.id
    assert entry.actor_user_id == 99
    assert entry.actor_role == "admin"
    assert entry.metadata["code"] == "HQ1"
    assert entry.metadata["name"] == "Headquarters 1"


# ------------------------------------------------------------------
# set_vendor_facilities / get_vendor_facilities
# ------------------------------------------------------------------

def test_set_and_get_vendor_facilities() -> None:
    svc, facility_repo, _, audit_repo = _make_service()

    f1 = facility_repo.create_facility("F01", "Facility One")
    f2 = facility_repo.create_facility("F02", "Facility Two")

    result = svc.set_vendor_facilities(1, [f1.id, f2.id], actor_user_id=10, actor_role="admin")

    assert {f.id for f in result} == {f1.id, f2.id}

    # audit entry
    entries = audit_repo.list(action="facility.assign")
    assert len(entries) == 1
    entry = entries[0]
    assert entry.target_type == "vendor"
    assert entry.target_id == 1
    assert entry.actor_user_id == 10
    assert entry.actor_role == "admin"
    assert entry.metadata["vendor_id"] == 1
    assert set(entry.metadata["facility_ids"]) == {f1.id, f2.id}

    # get_vendor_facilities reflects the new assignment
    fetched = svc.get_vendor_facilities(1)
    assert {f.id for f in fetched} == {f1.id, f2.id}


def test_set_vendor_facilities_replaces_previous_assignment() -> None:
    svc, facility_repo, _, _ = _make_service()

    f1 = facility_repo.create_facility("A1", "Alpha")
    f2 = facility_repo.create_facility("B1", "Beta")

    svc.set_vendor_facilities(1, [f1.id])
    svc.set_vendor_facilities(1, [f2.id])

    fetched = svc.get_vendor_facilities(1)
    assert len(fetched) == 1
    assert fetched[0].id == f2.id


# ------------------------------------------------------------------
# Error cases — invalid facility id
# ------------------------------------------------------------------

def test_set_vendor_facilities_invalid_facility_raises_404() -> None:
    svc, _, _, _ = _make_service()

    with pytest.raises(CodedHTTPException) as exc_info:
        svc.set_vendor_facilities(1, [9999])

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "not_found"


# ------------------------------------------------------------------
# Error cases — non-existent vendor
# ------------------------------------------------------------------

def test_get_vendor_facilities_unknown_vendor_raises_404() -> None:
    svc, _, _, _ = _make_service()

    with pytest.raises(CodedHTTPException) as exc_info:
        svc.get_vendor_facilities(9999)

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "not_found"


def test_set_vendor_facilities_unknown_vendor_raises_404() -> None:
    svc, facility_repo, _, _ = _make_service()
    f = facility_repo.create_facility("X1", "X Facility")

    with pytest.raises(CodedHTTPException) as exc_info:
        svc.set_vendor_facilities(9999, [f.id])

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "not_found"


# ------------------------------------------------------------------
# get_employee_facilities / set_employee_facilities
# ------------------------------------------------------------------

def test_set_and_get_employee_facilities() -> None:
    svc, facility_repo, _, audit_repo = _make_service()

    f1 = facility_repo.create_facility("E01", "Employee Facility 1")
    f2 = facility_repo.create_facility("E02", "Employee Facility 2")

    result = svc.set_employee_facilities(10, [f1.id, f2.id], actor_user_id=99, actor_role="admin")

    assert {f.id for f in result} == {f1.id, f2.id}

    entries = audit_repo.list(action="facility.assign")
    assert len(entries) == 1
    entry = entries[0]
    assert entry.target_type == "employee"
    assert entry.target_id == 10
    assert entry.actor_user_id == 99
    assert entry.actor_role == "admin"
    assert entry.metadata["employee_id"] == 10
    assert set(entry.metadata["facility_ids"]) == {f1.id, f2.id}

    fetched = svc.get_employee_facilities(10)
    assert {f.id for f in fetched} == {f1.id, f2.id}


def test_set_employee_facilities_replaces_previous() -> None:
    svc, facility_repo, _, _ = _make_service()

    f1 = facility_repo.create_facility("E01", "Emp Fac 1")
    f2 = facility_repo.create_facility("E02", "Emp Fac 2")

    svc.set_employee_facilities(10, [f1.id])
    svc.set_employee_facilities(10, [f2.id])

    fetched = svc.get_employee_facilities(10)
    assert len(fetched) == 1
    assert fetched[0].id == f2.id


def test_set_employee_facilities_empty_clears_assignment() -> None:
    svc, facility_repo, _, _ = _make_service()

    f = facility_repo.create_facility("E01", "Emp Fac 1")
    svc.set_employee_facilities(10, [f.id])
    svc.set_employee_facilities(10, [])

    assert svc.get_employee_facilities(10) == []


def test_set_employee_facilities_invalid_facility_raises_404() -> None:
    svc, _, _, _ = _make_service()

    with pytest.raises(CodedHTTPException) as exc_info:
        svc.set_employee_facilities(10, [9999])

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "not_found"


def test_get_employee_facilities_unknown_employee_returns_empty() -> None:
    svc, _, _, _ = _make_service()

    # No facility assignment means unrestricted — returns empty list, not 404
    result = svc.get_employee_facilities(9999)
    assert result == []
