"""Employee-facing vendor browsing, menu browsing, and meal selection APIs."""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from backend.core.vendor_identity import get_vendor_profile_repository
from backend.main import app
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository, OrderItemSnapshot
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


def _meal_date(days_from_today: int = 0) -> str:
    return (date.today() + timedelta(days=days_from_today)).isoformat()


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
    assert body["order_id"] is not None
    assert body["employee_id"] == 100
    assert body["vendor_id"] == 1
    assert body["item_id"] == item.id
    assert body["item_name"] == "Rice Bowl"
    assert body["quantity"] == 2
    assert body["unit_price_cents"] == 120
    assert body["total_price_cents"] == 240

    selections = client.get("/employee/me/selections", headers=_h(100)).json()
    assert [selection["id"] for selection in selections] == [body["id"]]


def test_create_order_records_multiple_items_and_total_price() -> None:
    client, item_repo, _ = _setup()
    rice = item_repo.create(vendor_id=1, name="Rice Bowl", price_cents=120, daily_quota=5)
    tea = item_repo.create(vendor_id=1, name="Tea", price_cents=40, daily_quota=10)

    resp = client.post(
        "/employee/vendors/1/orders",
        headers=_h(100),
        json={
            "items": [
                {"item_id": rice.id, "quantity": 2},
                {"item_id": tea.id, "quantity": 1},
            ]
        },
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["employee_id"] == 100
    assert body["vendor_id"] == 1
    assert body["status"] == "pending"
    assert body["total_price_cents"] == 280
    assert [(item["item_name"], item["quantity"]) for item in body["items"]] == [
        ("Rice Bowl", 2),
        ("Tea", 1),
    ]


def test_my_orders_are_scoped_by_employee() -> None:
    client, item_repo, _ = _setup()
    item = item_repo.create(vendor_id=1, name="Rice Bowl", price_cents=120)
    client.post(
        "/employee/vendors/1/orders",
        headers=_h(100),
        json={"items": [{"item_id": item.id, "quantity": 1}]},
    )

    resp = client.get("/employee/me/orders", headers=_h(200))

    assert resp.status_code == 200
    assert resp.json() == []


def test_cancel_pending_order_marks_order_cancelled() -> None:
    client, item_repo, _ = _setup()
    item = item_repo.create(vendor_id=1, name="Rice Bowl", price_cents=120)
    order = client.post(
        "/employee/vendors/1/orders",
        headers=_h(100),
        json={"items": [{"item_id": item.id, "quantity": 1}]},
    ).json()

    resp = client.post(f"/employee/me/orders/{order['id']}/cancel", headers=_h(100))

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "cancelled"
    assert body["cancelled_at"] is not None


def test_create_order_sums_duplicate_item_quantities_for_quota() -> None:
    client, item_repo, _ = _setup()
    item = item_repo.create(vendor_id=1, name="Rice Bowl", price_cents=120, daily_quota=2)

    resp = client.post(
        "/employee/vendors/1/orders",
        headers=_h(100),
        json={
            "items": [
                {"item_id": item.id, "quantity": 1},
                {"item_id": item.id, "quantity": 2},
            ]
        },
    )

    assert resp.status_code == 409
    assert resp.json()["code"] == "QUOTA_EXHAUSTED"


def test_create_order_tracks_quota_by_meal_date() -> None:
    client, item_repo, _ = _setup()
    item = item_repo.create(vendor_id=1, name="Rice Bowl", price_cents=120, daily_quota=2)
    meal_date = _meal_date()
    other_meal_date = _meal_date(1)
    client.post(
        "/employee/vendors/1/orders",
        headers=_h(100),
        json={"meal_date": meal_date, "items": [{"item_id": item.id, "quantity": 2}]},
    )

    same_date = client.post(
        "/employee/vendors/1/orders",
        headers=_h(200),
        json={"meal_date": meal_date, "items": [{"item_id": item.id, "quantity": 1}]},
    )
    other_date = client.post(
        "/employee/vendors/1/orders",
        headers=_h(200),
        json={"meal_date": other_meal_date, "items": [{"item_id": item.id, "quantity": 1}]},
    )

    assert same_date.status_code == 409
    assert same_date.json()["code"] == "QUOTA_EXHAUSTED"
    assert other_date.status_code == 201
    assert other_date.json()["meal_date"] == other_meal_date


def test_create_order_rejects_meal_date_outside_next_seven_days() -> None:
    client, item_repo, _ = _setup()
    item = item_repo.create(vendor_id=1, name="Rice Bowl", price_cents=120)

    past = client.post(
        "/employee/vendors/1/orders",
        headers=_h(100),
        json={"meal_date": _meal_date(-1), "items": [{"item_id": item.id, "quantity": 1}]},
    )
    too_far = client.post(
        "/employee/vendors/1/orders",
        headers=_h(100),
        json={"meal_date": _meal_date(7), "items": [{"item_id": item.id, "quantity": 1}]},
    )
    last_allowed = client.post(
        "/employee/vendors/1/orders",
        headers=_h(100),
        json={"meal_date": _meal_date(6), "items": [{"item_id": item.id, "quantity": 1}]},
    )

    assert past.status_code == 400
    assert past.json()["code"] == "validation_error"
    assert too_far.status_code == 400
    assert too_far.json()["code"] == "validation_error"
    assert last_allowed.status_code == 201


def test_draw_random_meal_uses_selected_vendors_and_remaining_quota() -> None:
    client, item_repo, _ = _setup()
    sold_out = item_repo.create(vendor_id=1, name="Sold Out", price_cents=80, daily_quota=1)
    available = item_repo.create(vendor_id=1, name="Noodles", price_cents=130, daily_quota=3)
    item_repo.create(vendor_id=1, name="Hidden Soup", price_cents=90, available=False)
    meal_date = _meal_date()
    client.post(
        "/employee/vendors/1/orders",
        headers=_h(100),
        json={"meal_date": meal_date, "items": [{"item_id": sold_out.id, "quantity": 1}]},
    )

    resp = client.post(
        "/employee/random-meals/draw",
        headers=_browse_h(),
        json={"meal_date": meal_date, "vendor_ids": [1]},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["meal_date"] == meal_date
    assert body["vendor"]["id"] == 1
    assert body["item"]["id"] == available.id
    assert body["remaining_quantity"] == 3


def test_draw_random_meal_returns_409_when_no_meals_remain() -> None:
    client, item_repo, _ = _setup()
    item = item_repo.create(vendor_id=1, name="Rice Bowl", price_cents=120, daily_quota=1)
    meal_date = _meal_date()
    client.post(
        "/employee/vendors/1/orders",
        headers=_h(100),
        json={"meal_date": meal_date, "items": [{"item_id": item.id, "quantity": 1}]},
    )

    resp = client.post(
        "/employee/random-meals/draw",
        headers=_browse_h(),
        json={"meal_date": meal_date, "vendor_ids": [1]},
    )

    assert resp.status_code == 409
    assert resp.json()["code"] == "no_random_meal_available"


def test_draw_random_meal_rejects_meal_date_outside_next_seven_days() -> None:
    client, item_repo, _ = _setup()
    item_repo.create(vendor_id=1, name="Rice Bowl", price_cents=120)

    resp = client.post(
        "/employee/random-meals/draw",
        headers=_browse_h(),
        json={"meal_date": _meal_date(7), "vendor_ids": [1]},
    )

    assert resp.status_code == 400
    assert resp.json()["code"] == "validation_error"


def test_confirm_random_meal_selection_records_meal_date() -> None:
    client, item_repo, _ = _setup()
    item = item_repo.create(vendor_id=1, name="Rice Bowl", price_cents=120)
    meal_date = _meal_date()

    resp = client.post(
        "/employee/vendors/1/selections",
        headers=_h(100),
        json={"item_id": item.id, "quantity": 1, "meal_date": meal_date},
    )

    assert resp.status_code == 201
    assert resp.json()["meal_date"] == meal_date


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
    assert resp.json()["code"] == "ITEM_UNAVAILABLE"


def test_select_auto_sold_out_item_returns_quota_exhausted() -> None:
    client, item_repo, selection_repo = _setup()
    item = item_repo.create(
        vendor_id=1,
        name="Last Bento",
        price_cents=120,
        available=False,
        daily_quota=1,
    )
    meal_date = date.today()
    selection_repo.create_order(
        employee_id=200,
        vendor_id=1,
        meal_date=meal_date,
        items=[
            OrderItemSnapshot(
                item_id=item.id,
                item_name=item.name,
                quantity=1,
                unit_price_cents=item.price_cents,
            )
        ],
    )

    resp = client.post(
        "/employee/vendors/1/selections",
        headers=_h(),
        json={"item_id": item.id, "quantity": 1, "meal_date": meal_date.isoformat()},
    )

    assert resp.status_code == 409
    assert resp.json()["code"] == "QUOTA_EXHAUSTED"


def test_select_quantity_over_daily_quota_returns_409() -> None:
    client, item_repo, _ = _setup()
    item = item_repo.create(vendor_id=1, name="Rice Bowl", price_cents=120, daily_quota=1)

    resp = client.post(
        "/employee/vendors/1/selections",
        headers=_h(),
        json={"item_id": item.id, "quantity": 2},
    )

    assert resp.status_code == 409
    assert resp.json()["code"] == "QUOTA_EXHAUSTED"


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
