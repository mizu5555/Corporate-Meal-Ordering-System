"""Digital pickup labels and pickup confirmation flow."""
from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from backend.core.vendor_identity import get_vendor_profile_repository
from backend.main import app
from backend.repositories.employee_selection_repository import (
    EmployeeSelectionRepository,
    OrderItemSnapshot,
)
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord
from backend.routes.employee_ordering import get_employee_selection_repository


def _seed_vendor_repo() -> VendorProfileRepository:
    repo = VendorProfileRepository()
    repo.seed(VendorRecord(id=1, name="Alice Bento", status="approved", address="No. 1"))
    repo.seed(VendorRecord(id=2, name="Bob Noodles", status="approved", address="No. 2"))
    repo.assign_facility(1, facility_id=10, code="F12A", name="Fab 12A")
    repo.assign_employee_facility(100, facility_id=10, code="F12A", name="Fab 12A")
    return repo


def _client(
    vendor_repo: VendorProfileRepository,
    selection_repo: EmployeeSelectionRepository,
) -> TestClient:
    app.dependency_overrides[get_vendor_profile_repository] = lambda: vendor_repo
    app.dependency_overrides[get_employee_selection_repository] = lambda: selection_repo
    return TestClient(app)


def _vh(vendor_id: int = 1, user_id: int | None = None) -> dict[str, str]:
    headers = {"x-user-role": "vendor_manager", "x-vendor-id": str(vendor_id)}
    if user_id is not None:
        headers["x-user-id"] = str(user_id)
    return headers


def _eh(user_id: int = 100) -> dict[str, str]:
    return {"x-user-role": "employee", "x-user-id": str(user_id)}


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_order_creation_assigns_pickup_code() -> None:
    selection_repo = EmployeeSelectionRepository()
    order = selection_repo.create_order(
        employee_id=100,
        vendor_id=1,
        meal_date=date(2026, 5, 28),
        items=[OrderItemSnapshot(item_id=1, item_name="Rice Bowl", quantity=2, unit_price_cents=120)],
    )

    assert order.pickup_code == "0528-0001"
    assert order.pickup_confirmed_at is None


def test_vendor_can_view_digital_pickup_label() -> None:
    vendor_repo = _seed_vendor_repo()
    selection_repo = EmployeeSelectionRepository()
    order = selection_repo.create_order(
        employee_id=100,
        vendor_id=1,
        meal_date=date(2026, 5, 28),
        items=[OrderItemSnapshot(item_id=1, item_name="Rice Bowl", quantity=2, unit_price_cents=120)],
    )

    resp = _client(vendor_repo, selection_repo).get(
        f"/vendor/me/orders/{order.id}/label",
        headers=_vh(1),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["pickup_code"] == "0528-0001"
    assert body["vendor_name"] == "Alice Bento"
    assert body["facility_names"] == ["Fab 12A"]
    assert body["items"] == [{"item_name": "Rice Bowl", "quantity": 2}]
    assert body["total_quantity"] == 2


def test_vendor_label_list_filters_by_date_and_status() -> None:
    vendor_repo = _seed_vendor_repo()
    selection_repo = EmployeeSelectionRepository()
    ready = selection_repo.create_order(
        employee_id=100,
        vendor_id=1,
        meal_date=date(2026, 5, 28),
        items=[],
    )
    other_date = selection_repo.create_order(
        employee_id=100,
        vendor_id=1,
        meal_date=date(2026, 5, 29),
        items=[],
    )
    selection_repo.update_order_status(vendor_id=1, order_id=ready.id, new_status="ready")
    selection_repo.update_order_status(vendor_id=1, order_id=other_date.id, new_status="ready")

    resp = _client(vendor_repo, selection_repo).get(
        "/vendor/me/orders/labels?meal_date=2026-05-28&status=ready",
        headers=_vh(1),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert [label["order_id"] for label in body] == [ready.id]


def test_employee_can_view_only_own_pickup_label() -> None:
    vendor_repo = _seed_vendor_repo()
    selection_repo = EmployeeSelectionRepository()
    order = selection_repo.create_order(
        employee_id=100,
        vendor_id=1,
        meal_date=date(2026, 5, 28),
        items=[],
    )
    client = _client(vendor_repo, selection_repo)

    own = client.get(f"/employee/me/orders/{order.id}/pickup-label", headers=_eh(100))
    other = client.get(f"/employee/me/orders/{order.id}/pickup-label", headers=_eh(200))

    assert own.status_code == 200
    assert own.json()["pickup_code"] == "0528-0001"
    assert other.status_code == 404


def test_pickup_confirm_requires_ready_order() -> None:
    vendor_repo = _seed_vendor_repo()
    selection_repo = EmployeeSelectionRepository()
    order = selection_repo.create_order(employee_id=100, vendor_id=1, items=[], meal_date=None)

    resp = _client(vendor_repo, selection_repo).post(
        f"/vendor/me/orders/{order.id}/pickup-confirm",
        headers=_vh(1),
    )

    assert resp.status_code == 409
    assert resp.json()["code"] == "order_not_ready_for_pickup"


def test_vendor_can_confirm_ready_pickup() -> None:
    vendor_repo = _seed_vendor_repo()
    selection_repo = EmployeeSelectionRepository()
    order = selection_repo.create_order(employee_id=100, vendor_id=1, items=[], meal_date=None)
    selection_repo.update_order_status(vendor_id=1, order_id=order.id, new_status="ready")

    resp = _client(vendor_repo, selection_repo).post(
        f"/vendor/me/orders/{order.id}/pickup-confirm",
        headers=_vh(1, user_id=77),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "delivered"
    assert body["pickup_confirmed_at"] is not None
    assert body["pickup_confirmed_by_user_id"] == 77


def test_vendor_cannot_view_other_vendors_label() -> None:
    vendor_repo = _seed_vendor_repo()
    selection_repo = EmployeeSelectionRepository()
    order = selection_repo.create_order(employee_id=100, vendor_id=2, items=[], meal_date=None)

    resp = _client(vendor_repo, selection_repo).get(
        f"/vendor/me/orders/{order.id}/label",
        headers=_vh(1),
    )

    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"
