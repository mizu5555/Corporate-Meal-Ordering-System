"""Tests for facility-based employee/vendor visibility (issue #65).

Verifies that:
- Employees assigned to a facility can only browse vendors serving that facility.
- Employees with no facility assignment can see all approved vendors (backward compat).
- Vendors with no facility assignment are visible to all employees.
- Cross-facility employees cannot see or access vendors outside their facility.
- draw_random_meal respects the same facility filter.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.core.audit import get_audit_log_repository
from backend.core.vendor_identity import get_vendor_profile_repository
from backend.main import app
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository
from backend.repositories.menu_item_repository import MenuItemRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord
from backend.routes.employee_ordering import get_employee_selection_repository
from backend.routes.vendor_menu import get_menu_item_repository
from backend.schemas.employee import RandomMealDrawRequest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _build_repos() -> tuple[VendorProfileRepository, MenuItemRepository, EmployeeSelectionRepository]:
    vendor_repo = VendorProfileRepository()

    # Vendor 1 — serves F12A only
    vendor_repo.seed(VendorRecord(id=1, name="Sunny Kitchen", status="approved"))
    vendor_repo.assign_facility(1, facility_id=10, code="F12A", name="Fab 12A")

    # Vendor 2 — serves F14B only
    vendor_repo.seed(VendorRecord(id=2, name="Fab 14 Bistro", status="approved"))
    vendor_repo.assign_facility(2, facility_id=20, code="F14B", name="Fab 14B")

    # Vendor 3 — no facility (visible to everyone)
    vendor_repo.seed(VendorRecord(id=3, name="Global Canteen", status="approved"))

    # Vendor 4 — pending, never visible
    vendor_repo.seed(VendorRecord(id=4, name="Not Yet Approved", status="pending"))

    # Employee 101 — belongs to F12A
    vendor_repo.assign_employee_facility(101, facility_id=10, code="F12A", name="Fab 12A")

    # Employee 102 — belongs to F14B
    vendor_repo.assign_employee_facility(102, facility_id=20, code="F14B", name="Fab 14B")

    # Employee 103 — no facility (sees everything)

    item_repo = MenuItemRepository()
    item_repo.create(vendor_id=1, category_id=None, name="Bento", price_cents=100, available=True)

    selection_repo = EmployeeSelectionRepository()
    return vendor_repo, item_repo, selection_repo


def _setup() -> tuple[TestClient, VendorProfileRepository, MenuItemRepository, EmployeeSelectionRepository]:
    vendor_repo, item_repo, selection_repo = _build_repos()
    app.dependency_overrides[get_vendor_profile_repository] = lambda: vendor_repo
    app.dependency_overrides[get_menu_item_repository] = lambda: item_repo
    app.dependency_overrides[get_employee_selection_repository] = lambda: selection_repo
    app.dependency_overrides[get_audit_log_repository] = lambda: AuditLogRepository()
    return TestClient(app), vendor_repo, item_repo, selection_repo


def _h(user_id: int) -> dict[str, str]:
    return {"x-user-role": "employee", "x-user-id": str(user_id)}


def teardown_function() -> None:
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# list_vendors facility filtering
# ---------------------------------------------------------------------------

def test_f12a_employee_sees_only_f12a_and_global_vendors() -> None:
    client, *_ = _setup()
    resp = client.get("/employee/vendors", headers=_h(101))
    assert resp.status_code == 200
    names = {v["name"] for v in resp.json()}
    assert "Sunny Kitchen" in names        # F12A ✓
    assert "Global Canteen" in names       # no facility → visible everywhere ✓
    assert "Fab 14 Bistro" not in names    # F14B — different facility ✗


def test_f14b_employee_sees_only_f14b_and_global_vendors() -> None:
    client, *_ = _setup()
    resp = client.get("/employee/vendors", headers=_h(102))
    assert resp.status_code == 200
    names = {v["name"] for v in resp.json()}
    assert "Fab 14 Bistro" in names        # F14B ✓
    assert "Global Canteen" in names       # no facility → visible everywhere ✓
    assert "Sunny Kitchen" not in names    # F12A — different facility ✗


def test_employee_with_no_facility_sees_all_approved_vendors() -> None:
    client, *_ = _setup()
    resp = client.get("/employee/vendors", headers=_h(103))
    assert resp.status_code == 200
    names = {v["name"] for v in resp.json()}
    assert names == {"Sunny Kitchen", "Fab 14 Bistro", "Global Canteen"}
    # Pending vendor never shown
    assert "Not Yet Approved" not in names


def test_pending_vendor_never_shown_regardless_of_facility() -> None:
    client, *_ = _setup()
    resp = client.get("/employee/vendors", headers=_h(103))
    assert resp.status_code == 200
    names = [v["name"] for v in resp.json()]
    assert "Not Yet Approved" not in names


# ---------------------------------------------------------------------------
# get_vendor facility guard
# ---------------------------------------------------------------------------

def test_get_vendor_in_same_facility_returns_200() -> None:
    client, *_ = _setup()
    resp = client.get("/employee/vendors/1", headers=_h(101))  # 101=F12A, vendor 1=F12A
    assert resp.status_code == 200
    assert resp.json()["name"] == "Sunny Kitchen"


def test_get_vendor_in_different_facility_returns_404() -> None:
    client, *_ = _setup()
    resp = client.get("/employee/vendors/2", headers=_h(101))  # 101=F12A, vendor 2=F14B
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"


def test_get_global_vendor_visible_to_any_employee() -> None:
    client, *_ = _setup()
    for uid in (101, 102, 103):
        resp = client.get("/employee/vendors/3", headers=_h(uid))
        assert resp.status_code == 200, f"Expected 200 for employee {uid}"


def test_get_vendor_no_facility_employee_can_access_all() -> None:
    client, *_ = _setup()
    for vendor_id in (1, 2, 3):
        resp = client.get(f"/employee/vendors/{vendor_id}", headers=_h(103))
        assert resp.status_code == 200, f"Employee 103 should see vendor {vendor_id}"


# ---------------------------------------------------------------------------
# list_menu facility guard
# ---------------------------------------------------------------------------

def test_list_menu_cross_facility_returns_404() -> None:
    client, *_ = _setup()
    resp = client.get("/employee/vendors/2/menu", headers=_h(101))  # 101=F12A, vendor 2=F14B
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"


def test_list_menu_same_facility_returns_200() -> None:
    client, *_ = _setup()
    resp = client.get("/employee/vendors/1/menu", headers=_h(101))
    assert resp.status_code == 200


def test_select_meal_persists_employee_facility() -> None:
    client, _, item_repo, _ = _setup()
    item = item_repo.create(vendor_id=1, category_id=None, name="Soup", price_cents=80, available=True)

    resp = client.post(
        "/employee/vendors/1/selections",
        headers=_h(101),
        json={"item_id": item.id, "quantity": 1, "facility_id": 10},
    )

    assert resp.status_code == 201
    assert resp.json()["facility_id"] == 10


def test_select_meal_cross_facility_returns_404() -> None:
    client, _, item_repo, _ = _setup()
    item = item_repo.create(vendor_id=2, category_id=None, name="Fab Bowl", price_cents=120, available=True)

    resp = client.post(
        "/employee/vendors/2/selections",
        headers=_h(101),
        json={"item_id": item.id, "quantity": 1, "facility_id": 10},
    )

    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"


# ---------------------------------------------------------------------------
# draw_random_meal facility filter
# ---------------------------------------------------------------------------

def _meal_date(days: int = 0) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def test_draw_random_meal_respects_facility_filter() -> None:
    client, vendor_repo, item_repo, _ = _setup()
    # Add an item to vendor 2 so it's a candidate if visible
    item_repo.create(vendor_id=2, category_id=None, name="Fab Bowl", price_cents=120, available=True)

    resp = client.post(
        "/employee/random-meals/draw",
        json={"meal_date": _meal_date(1)},
        headers=_h(101),  # F12A employee
    )
    assert resp.status_code == 200
    # Only F12A vendor (id=1) and global (id=3) are candidates → never vendor 2
    assert resp.json()["vendor"]["id"] != 2


def test_draw_random_meal_no_facility_employee_uses_all_vendors() -> None:
    client, vendor_repo, item_repo, _ = _setup()
    item_repo.create(vendor_id=2, category_id=None, name="Fab Bowl", price_cents=120, available=True)

    # Employee 103 has no facility → all vendors are candidates; just assert 200
    resp = client.post(
        "/employee/random-meals/draw",
        json={"meal_date": _meal_date(1)},
        headers=_h(103),
    )
    assert resp.status_code == 200
