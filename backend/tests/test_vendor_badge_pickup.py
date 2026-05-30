"""Unit tests for GET /vendor/me/orders/by-badge/{badge_code}."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.user_directory import get_user_repository
from backend.repositories.user_repository import UserRepository
from backend.routes.employee_ordering import get_employee_selection_repository
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository
from backend.core.vendor_identity import get_vendor_profile_repository
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord


def _seed_vendor_repo():
    # mirror test_vendor_orders.py: seed approved VendorRecords directly
    repo = VendorProfileRepository()
    repo.seed(VendorRecord(id=1, name="Alice Bento", status="approved", address="No. 1"))
    repo.seed(VendorRecord(id=2, name="Bob Noodles", status="approved", address="No. 2"))
    return repo


def _ready_order(sel, *, vendor_id, employee_id, meal_date):
    o = sel.create_order(employee_id=employee_id, vendor_id=vendor_id, items=[], meal_date=meal_date)
    for s in ("confirmed", "preparing", "ready"):
        sel.update_order_status(vendor_id=vendor_id, order_id=o.id, new_status=s)
    return o.id


@pytest.fixture()
def env():
    today = date.today()
    sel = EmployeeSelectionRepository()
    users = UserRepository()
    users.add(id=10, display_name="王小明", role="employee", badge_code="EMP-0001")
    users.add(id=20, display_name="John Smith", role="employee", badge_code="EMP-0002")
    o1 = _ready_order(sel, vendor_id=1, employee_id=10, meal_date=today)
    _ready_order(sel, vendor_id=1, employee_id=20, meal_date=today)   # other employee, same store
    _ready_order(sel, vendor_id=2, employee_id=20, meal_date=today)   # emp20 also has order in store 2

    vendor_repo = _seed_vendor_repo()

    app.dependency_overrides[get_employee_selection_repository] = lambda: sel
    app.dependency_overrides[get_user_repository] = lambda: users
    app.dependency_overrides[get_vendor_profile_repository] = lambda: vendor_repo
    yield {"o1": o1}
    app.dependency_overrides.clear()


@pytest.fixture()
def client():
    return TestClient(app)


def _vendor(vendor_id):
    return {"x-user-role": "vendor_manager", "x-vendor-id": str(vendor_id)}


def test_returns_only_that_employees_ready_order_in_this_store(client, env):
    resp = client.get("/vendor/me/orders/by-badge/EMP-0001", headers=_vendor(1))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [o["id"] for o in body] == [env["o1"]]            # distinguishable: not emp20's order
    assert body[0]["employee_badge_code"] == "EMP-0001"      # by-badge attaches identity
    assert body[0]["masked_name"] == "王*明"
    assert body[0].get("employee_id") is None                # no uid leak


def test_badge_not_found(client, env):
    resp = client.get("/vendor/me/orders/by-badge/EMP-9999", headers=_vendor(1))
    assert resp.status_code == 404
    assert "badge_not_found" in resp.text


def test_cross_store_isolation(client, env):
    # emp10 (EMP-0001) has no order in store 2 -> empty
    resp = client.get("/vendor/me/orders/by-badge/EMP-0001", headers=_vendor(2))
    assert resp.status_code == 200
    assert resp.json() == []


def test_non_vendor_forbidden(client, env):
    resp = client.get("/vendor/me/orders/by-badge/EMP-0001", headers={"x-user-role": "employee", "x-user-id": "10"})
    assert resp.status_code == 403
