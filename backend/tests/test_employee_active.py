"""Unit tests for the is_active enforcement in require_employee.

These tests override ``get_employee_active_check`` explicitly (instead of relying
on the autouse bypass) to verify the guard itself — simulating both active and
disabled employees without a real database connection.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.core.employee_identity import get_employee_active_check
from backend.core.errors import CodedHTTPException
from backend.core.vendor_identity import get_vendor_profile_repository
from backend.main import app
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord


def _setup_vendor_repo() -> None:
    vendor_repo = VendorProfileRepository()
    vendor_repo.seed(
        VendorRecord(
            id=1,
            name="Test Bento",
            status="approved",
            address="No. 1",
            business_hours="11:00-14:00",
            contact_phone="0912-000-000",
            contact_email="test@example.com",
        )
    )
    app.dependency_overrides[get_vendor_profile_repository] = lambda: vendor_repo


def _h(user_id: int = 42) -> dict[str, str]:
    return {"x-user-role": "employee", "x-user-id": str(user_id)}


def teardown_function() -> None:
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Active employee passes through
# ---------------------------------------------------------------------------


def test_active_employee_can_access_endpoint() -> None:
    _setup_vendor_repo()
    # Override: simulate an active employee (no-op check)
    app.dependency_overrides[get_employee_active_check] = lambda: (lambda _: None)

    client = TestClient(app)
    resp = client.get("/employee/vendors", headers=_h())

    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Disabled employee is rejected
# ---------------------------------------------------------------------------


def _raise_disabled(employee_id: int) -> None:
    raise CodedHTTPException(
        status_code=403,
        code="account_disabled",
        detail="This account has been disabled",
    )


def test_disabled_employee_gets_403_on_browse() -> None:
    _setup_vendor_repo()
    app.dependency_overrides[get_employee_active_check] = lambda: _raise_disabled

    client = TestClient(app)
    resp = client.get("/employee/vendors", headers=_h())

    assert resp.status_code == 403
    body = resp.json()
    assert body["code"] == "account_disabled"


def test_disabled_employee_gets_403_on_order() -> None:
    from backend.repositories.employee_selection_repository import EmployeeSelectionRepository
    from backend.repositories.menu_item_repository import MenuItemRepository
    from backend.routes.employee_ordering import get_employee_selection_repository
    from backend.routes.vendor_menu import get_menu_item_repository

    _setup_vendor_repo()
    app.dependency_overrides[get_menu_item_repository] = lambda: MenuItemRepository()
    app.dependency_overrides[get_employee_selection_repository] = lambda: EmployeeSelectionRepository()
    app.dependency_overrides[get_employee_active_check] = lambda: _raise_disabled

    client = TestClient(app)
    resp = client.post(
        "/employee/vendors/1/orders",
        json={"meal_date": "2099-01-01", "items": [{"menu_item_id": 1, "quantity": 1}]},
        headers=_h(),
    )

    assert resp.status_code == 403
    assert resp.json()["code"] == "account_disabled"


# ---------------------------------------------------------------------------
# Non-employee role is still rejected (regression)
# ---------------------------------------------------------------------------


def test_non_employee_role_still_rejected() -> None:
    _setup_vendor_repo()
    app.dependency_overrides[get_employee_active_check] = lambda: (lambda _: None)

    client = TestClient(app)
    resp = client.get("/employee/vendors", headers={"x-user-role": "vendor_manager", "x-user-id": "1"})

    assert resp.status_code == 403
