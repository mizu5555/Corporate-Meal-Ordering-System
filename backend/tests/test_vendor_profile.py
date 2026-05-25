"""GET / PATCH /vendor/me/profile and GET /vendor/me/orders."""
from fastapi.testclient import TestClient

from backend.core.vendor_identity import get_vendor_profile_repository
from backend.main import app
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord
from backend.routes.employee_ordering import get_employee_selection_repository


def _seed() -> VendorProfileRepository:
    repo = VendorProfileRepository()
    repo.seed(VendorRecord(id=1, name="Alice Bento", status="approved", address="Old"))
    repo.assign_facility(1, facility_id=10, code="F12A", name="Fab 12A")
    return repo


def _client(repo: VendorProfileRepository) -> TestClient:
    app.dependency_overrides[get_vendor_profile_repository] = lambda: repo
    return TestClient(app)


def _vendor_headers(vid: int = 1) -> dict[str, str]:
    return {"x-user-role": "vendor_manager", "x-vendor-id": str(vid)}


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_get_profile_returns_vendor_with_facilities() -> None:
    response = _client(_seed()).get("/vendor/me/profile", headers=_vendor_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Alice Bento"
    assert body["status"] == "approved"
    assert body["served_facilities"] == [{"id": 10, "code": "F12A", "name": "Fab 12A"}]


def test_patch_updates_address_only() -> None:
    response = _client(_seed()).patch(
        "/vendor/me/profile",
        headers=_vendor_headers(),
        json={"address": "New address"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["address"] == "New address"
    assert body["name"] == "Alice Bento"


def test_patch_silently_ignores_served_facilities_in_body() -> None:
    response = _client(_seed()).patch(
        "/vendor/me/profile",
        headers=_vendor_headers(),
        json={"served_facilities": [{"id": 99, "code": "X", "name": "X"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert {f["code"] for f in body["served_facilities"]} == {"F12A"}


def test_unauthenticated_role_403() -> None:
    response = _client(_seed()).get(
        "/vendor/me/profile",
        headers={"x-user-role": "employee", "x-vendor-id": "1"},
    )
    assert response.status_code == 403


# --- /vendor/me/orders ---


def _orders_client(
    vendor_repo: VendorProfileRepository,
    selection_repo: EmployeeSelectionRepository,
) -> TestClient:
    app.dependency_overrides[get_vendor_profile_repository] = lambda: vendor_repo
    app.dependency_overrides[get_employee_selection_repository] = lambda: selection_repo
    return TestClient(app)


def test_list_vendor_orders_returns_own_selections() -> None:
    vendor_repo = _seed()
    selection_repo = EmployeeSelectionRepository()
    selection_repo.create(employee_id=10, vendor_id=1, item_id=5, item_name="Rice Bowl", quantity=2, unit_price_cents=120)
    selection_repo.create(employee_id=11, vendor_id=1, item_id=6, item_name="Tea", quantity=1, unit_price_cents=40)

    resp = _orders_client(vendor_repo, selection_repo).get(
        "/vendor/me/orders", headers=_vendor_headers(1)
    )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["item_name"] == "Rice Bowl"
    assert body[0]["total_price_cents"] == 240
    assert body[1]["item_name"] == "Tea"


def test_list_vendor_orders_excludes_other_vendors_selections() -> None:
    vendor_repo = _seed()
    selection_repo = EmployeeSelectionRepository()
    selection_repo.create(employee_id=10, vendor_id=2, item_id=9, item_name="Other Bento", quantity=1, unit_price_cents=100)

    resp = _orders_client(vendor_repo, selection_repo).get(
        "/vendor/me/orders", headers=_vendor_headers(1)
    )

    assert resp.status_code == 200
    assert resp.json() == []


def test_list_vendor_orders_returns_empty_when_no_orders() -> None:
    resp = _orders_client(_seed(), EmployeeSelectionRepository()).get(
        "/vendor/me/orders", headers=_vendor_headers(1)
    )

    assert resp.status_code == 200
    assert resp.json() == []


def test_list_vendor_orders_requires_vendor_manager_role() -> None:
    resp = _orders_client(_seed(), EmployeeSelectionRepository()).get(
        "/vendor/me/orders",
        headers={"x-user-role": "employee", "x-vendor-id": "1"},
    )

    assert resp.status_code == 403
    assert resp.json()["code"] == "forbidden"
