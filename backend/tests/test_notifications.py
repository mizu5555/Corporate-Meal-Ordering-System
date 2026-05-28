"""In-app notifications for employee order events."""
from fastapi.testclient import TestClient

from backend.core.audit import get_audit_log_repository
from backend.core.vendor_identity import get_vendor_profile_repository
from backend.main import app
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository
from backend.repositories.menu_item_repository import MenuItemRepository
from backend.repositories.notification_repository import NotificationRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord
from backend.routes.employee_ordering import get_employee_selection_repository
from backend.routes.notifications import get_notification_repository
from backend.routes.vendor_menu import get_menu_item_repository


def _setup() -> tuple[TestClient, MenuItemRepository, EmployeeSelectionRepository, NotificationRepository]:
    vendor_repo = VendorProfileRepository()
    vendor_repo.seed(VendorRecord(id=1, name="Alice Bento", status="approved"))
    vendor_repo.assign_facility(1, facility_id=10, code="F12A", name="Fab 12A")
    vendor_repo.assign_employee_facility(100, facility_id=10, code="F12A", name="Fab 12A")

    item_repo = MenuItemRepository()
    selection_repo = EmployeeSelectionRepository()
    notification_repo = NotificationRepository()

    app.dependency_overrides[get_vendor_profile_repository] = lambda: vendor_repo
    app.dependency_overrides[get_menu_item_repository] = lambda: item_repo
    app.dependency_overrides[get_employee_selection_repository] = lambda: selection_repo
    app.dependency_overrides[get_notification_repository] = lambda: notification_repo
    app.dependency_overrides[get_audit_log_repository] = lambda: AuditLogRepository()
    return TestClient(app), item_repo, selection_repo, notification_repo


def _employee_headers(user_id: int = 100) -> dict[str, str]:
    return {"x-user-role": "employee", "x-user-id": str(user_id)}


def _vendor_headers(vendor_id: int = 1) -> dict[str, str]:
    return {"x-user-role": "vendor_manager", "x-vendor-id": str(vendor_id)}


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_order_creation_enqueues_unread_notification_for_employee() -> None:
    client, item_repo, _, _ = _setup()
    item = item_repo.create(vendor_id=1, name="Rice Bowl", price_cents=120)

    resp = client.post(
        "/employee/vendors/1/orders",
        headers=_employee_headers(100),
        json={"items": [{"item_id": item.id, "quantity": 2}]},
    )

    assert resp.status_code == 201
    order = resp.json()

    notifications = client.get("/me/notifications", headers=_employee_headers(100))
    assert notifications.status_code == 200
    body = notifications.json()
    assert len(body) == 1
    assert body[0]["recipient_user_id"] == 100
    assert body[0]["type"] == "order_placed"
    assert body[0]["read_at"] is None
    assert body[0]["sent_at"] is not None
    assert body[0]["payload"] == {
        "order_id": order["id"],
        "vendor_id": 1,
        "status": "pending",
        "meal_date": order["meal_date"],
        "total_price_cents": 240,
    }


def test_legacy_meal_selection_enqueues_order_notification() -> None:
    client, item_repo, _, _ = _setup()
    item = item_repo.create(vendor_id=1, name="Rice Bowl", price_cents=120)

    resp = client.post(
        "/employee/vendors/1/selections",
        headers=_employee_headers(100),
        json={"item_id": item.id, "quantity": 1},
    )

    assert resp.status_code == 201
    selection = resp.json()

    notifications = client.get("/me/notifications", headers=_employee_headers(100))
    assert notifications.status_code == 200
    body = notifications.json()
    assert len(body) == 1
    assert body[0]["type"] == "order_placed"
    assert body[0]["payload"]["order_id"] == selection["order_id"]
    assert body[0]["payload"]["total_price_cents"] == 120


def test_vendor_status_update_enqueues_notification_for_ordering_employee() -> None:
    client, _, selection_repo, _ = _setup()
    order = selection_repo.create_order(employee_id=100, vendor_id=1, items=[], meal_date=None)

    resp = client.patch(
        f"/vendor/me/orders/{order.id}/status",
        headers=_vendor_headers(1),
        json={"status": "confirmed"},
    )

    assert resp.status_code == 200

    notifications = client.get("/me/notifications", headers=_employee_headers(100))
    assert notifications.status_code == 200
    body = notifications.json()
    assert len(body) == 1
    assert body[0]["type"] == "order_status_updated"
    assert body[0]["payload"] == {
        "order_id": order.id,
        "vendor_id": 1,
        "status": "confirmed",
        "meal_date": None,
    }


def test_my_notifications_returns_only_current_users_unread_notifications() -> None:
    client, _, _, notification_repo = _setup()
    notification_repo.create(
        recipient_user_id=100,
        type="order_placed",
        payload={"order_id": 1},
    )
    notification_repo.create(
        recipient_user_id=200,
        type="order_placed",
        payload={"order_id": 2},
    )

    resp = client.get("/me/notifications", headers=_employee_headers(100))

    assert resp.status_code == 200
    body = resp.json()
    assert [notification["recipient_user_id"] for notification in body] == [100]
    assert [notification["payload"]["order_id"] for notification in body] == [1]
