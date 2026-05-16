"""Employee-facing vendor browsing, menu browsing, and meal selection APIs."""
from fastapi.testclient import TestClient

from backend.core.vendor_identity import get_vendor_profile_repository
from backend.main import app
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository
from backend.repositories.menu_item_repository import MenuItemRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord
from backend.routes.employee_ordering import get_employee_selection_repository
from backend.routes.vendor_menu import get_menu_item_repository


def _setup() -> tuple[TestClient, MenuItemRepository, EmployeeSelectionRepository]:
    vendor_repo = VendorProfileRepository()
    vendor_repo.seed(
        VendorRecord(
            id=1,
            name="Alice Bento",
            status="approved",
            address="No. 1",
            business_hours="11:00-14:00",
            contact_phone="0912-000-000",
            contact_email="alice@example.com",
        )
    )
    vendor_repo.seed(VendorRecord(id=2, name="Pending Bento", status="pending"))
    vendor_repo.assign_facility(1, facility_id=10, code="F12A", name="Fab 12A")

    item_repo = MenuItemRepository()
    selection_repo = EmployeeSelectionRepository()

    app.dependency_overrides[get_vendor_profile_repository] = lambda: vendor_repo
    app.dependency_overrides[get_menu_item_repository] = lambda: item_repo
    app.dependency_overrides[get_employee_selection_repository] = lambda: selection_repo
    return TestClient(app), item_repo, selection_repo


def _h(user_id: int = 100) -> dict[str, str]:
    return {"x-user-role": "employee", "x-user-id": str(user_id)}


def _browse_h() -> dict[str, str]:
    return {"x-user-role": "employee"}


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_list_vendors_returns_approved_vendors_only() -> None:
    client, _, _ = _setup()

    resp = client.get("/employee/vendors", headers=_browse_h())

    assert resp.status_code == 200
    body = resp.json()
    assert [vendor["name"] for vendor in body] == ["Alice Bento"]
    assert body[0]["served_facilities"] == [{"id": 10, "code": "F12A", "name": "Fab 12A"}]


def test_get_vendor_returns_public_vendor_information() -> None:
    client, _, _ = _setup()

    resp = client.get("/employee/vendors/1", headers=_browse_h())

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Alice Bento"
    assert body["address"] == "No. 1"
    assert body["business_hours"] == "11:00-14:00"
    assert body["contact_phone"] == "0912-000-000"


def test_pending_vendor_is_hidden_from_employee() -> None:
    client, _, _ = _setup()

    resp = client.get("/employee/vendors/2", headers=_browse_h())

    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"


def test_list_menu_defaults_to_available_items() -> None:
    client, item_repo, _ = _setup()
    item_repo.create(vendor_id=1, category_id=7, name="Rice Bowl", price_cents=120, available=True)
    item_repo.create(vendor_id=1, category_id=7, name="Sold Out Soup", price_cents=80, available=False)
    item_repo.create(vendor_id=1, category_id=8, name="Tea", price_cents=40, available=True)

    resp = client.get("/employee/vendors/1/menu?category_id=7", headers=_browse_h())

    assert resp.status_code == 200
    assert [item["name"] for item in resp.json()] == ["Rice Bowl"]


def test_select_meal_records_quantity_and_total_price() -> None:
    client, item_repo, _ = _setup()
    item = item_repo.create(vendor_id=1, name="Rice Bowl", price_cents=120, daily_quota=5)

    resp = client.post(
        "/employee/vendors/1/selections",
        headers=_h(100),
        json={"item_id": item.id, "quantity": 2},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["employee_id"] == 100
    assert body["vendor_id"] == 1
    assert body["item_id"] == item.id
    assert body["item_name"] == "Rice Bowl"
    assert body["quantity"] == 2
    assert body["unit_price_cents"] == 120
    assert body["total_price_cents"] == 240

    selections = client.get("/employee/me/selections", headers=_h(100)).json()
    assert [selection["id"] for selection in selections] == [body["id"]]


def test_my_selections_are_scoped_by_employee() -> None:
    client, item_repo, _ = _setup()
    item = item_repo.create(vendor_id=1, name="Rice Bowl", price_cents=120)
    client.post("/employee/vendors/1/selections", headers=_h(100), json={"item_id": item.id, "quantity": 1})

    resp = client.get("/employee/me/selections", headers=_h(200))

    assert resp.status_code == 200
    assert resp.json() == []


def test_select_unavailable_item_returns_409() -> None:
    client, item_repo, _ = _setup()
    item = item_repo.create(vendor_id=1, name="Sold Out Soup", price_cents=80, available=False)

    resp = client.post(
        "/employee/vendors/1/selections",
        headers=_h(),
        json={"item_id": item.id, "quantity": 1},
    )

    assert resp.status_code == 409
    assert resp.json()["code"] == "item_unavailable"


def test_select_quantity_over_daily_quota_returns_409() -> None:
    client, item_repo, _ = _setup()
    item = item_repo.create(vendor_id=1, name="Rice Bowl", price_cents=120, daily_quota=1)

    resp = client.post(
        "/employee/vendors/1/selections",
        headers=_h(),
        json={"item_id": item.id, "quantity": 2},
    )

    assert resp.status_code == 409
    assert resp.json()["code"] == "quantity_exceeds_daily_quota"


def test_employee_endpoints_require_employee_role() -> None:
    client, _, _ = _setup()

    resp = client.get("/employee/vendors", headers={"x-user-role": "vendor_manager"})

    assert resp.status_code == 403
    assert resp.json()["code"] == "forbidden"


def test_select_meal_requires_employee_id() -> None:
    client, item_repo, _ = _setup()
    item = item_repo.create(vendor_id=1, name="Rice Bowl", price_cents=120)

    resp = client.post(
        "/employee/vendors/1/selections",
        headers={"x-user-role": "employee"},
        json={"item_id": item.id, "quantity": 1},
    )

    assert resp.status_code == 400
    assert resp.json()["code"] == "validation_error"
