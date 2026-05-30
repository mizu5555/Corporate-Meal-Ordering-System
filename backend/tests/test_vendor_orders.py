"""GET /vendor/me/orders, GET /vendor/me/orders/{id}, PATCH /vendor/me/orders/{id}/status."""
from fastapi.testclient import TestClient

from backend.core.vendor_identity import get_vendor_profile_repository
from backend.main import app
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord
from backend.routes.employee_ordering import get_employee_selection_repository
from backend.services.vendor_order_service import VendorOrderService


def _seed_vendor_repo() -> VendorProfileRepository:
    repo = VendorProfileRepository()
    repo.seed(VendorRecord(id=1, name="Alice Bento", status="approved", address="No. 1"))
    repo.seed(VendorRecord(id=2, name="Bob Noodles", status="approved", address="No. 2"))
    repo.assign_facility(1, facility_id=10, code="F12A", name="Fab 12A")
    repo.assign_facility(1, facility_id=20, code="F14B", name="Fab 14B")
    repo.assign_facility(2, facility_id=20, code="F14B", name="Fab 14B")
    return repo


def _client(
    vendor_repo: VendorProfileRepository,
    selection_repo: EmployeeSelectionRepository,
) -> TestClient:
    app.dependency_overrides[get_vendor_profile_repository] = lambda: vendor_repo
    app.dependency_overrides[get_employee_selection_repository] = lambda: selection_repo
    return TestClient(app)


def _vh(vid: int = 1) -> dict[str, str]:
    return {"x-user-role": "vendor_manager", "x-vendor-id": str(vid)}


def teardown_function() -> None:
    app.dependency_overrides.clear()


# --- list ---

def test_list_returns_orders_for_own_vendor() -> None:
    vendor_repo = _seed_vendor_repo()
    selection_repo = EmployeeSelectionRepository()
    selection_repo.create_order(employee_id=10, vendor_id=1, items=[], meal_date=None)
    # another vendor's order should not appear
    selection_repo.create_order(employee_id=20, vendor_id=2, items=[], meal_date=None)

    resp = _client(vendor_repo, selection_repo).get("/vendor/me/orders", headers=_vh(1))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["vendor_id"] == 1
    assert body[0].get("employee_id") is None
    assert body[0].get("employee_badge_code") is None
    assert body[0].get("masked_name") is None
    assert "items" in body[0]
    assert "status" in body[0]


def test_list_returns_empty_when_no_orders() -> None:
    resp = _client(_seed_vendor_repo(), EmployeeSelectionRepository()).get(
        "/vendor/me/orders", headers=_vh(1)
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_my_facilities_returns_vendor_facilities() -> None:
    resp = _client(_seed_vendor_repo(), EmployeeSelectionRepository()).get(
        "/vendor/me/facilities", headers=_vh(1)
    )

    assert resp.status_code == 200
    assert resp.json() == [
        {"id": 10, "code": "F12A", "name": "Fab 12A"},
        {"id": 20, "code": "F14B", "name": "Fab 14B"},
    ]


def test_list_filters_orders_by_facility() -> None:
    vendor_repo = _seed_vendor_repo()
    selection_repo = EmployeeSelectionRepository()
    selection_repo.create_order(employee_id=10, vendor_id=1, items=[], meal_date=None, facility_id=10)
    selection_repo.create_order(employee_id=20, vendor_id=1, items=[], meal_date=None, facility_id=20)

    resp = _client(vendor_repo, selection_repo).get("/vendor/me/orders?facility_id=10", headers=_vh(1))

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["facility_id"] == 10
    assert body[0].get("employee_id") is None
    assert body[0].get("employee_badge_code") is None
    assert body[0].get("masked_name") is None


def test_list_rejects_unserved_facility_filter() -> None:
    resp = _client(_seed_vendor_repo(), EmployeeSelectionRepository()).get(
        "/vendor/me/orders?facility_id=99", headers=_vh(1)
    )

    assert resp.status_code == 403
    assert resp.json()["code"] == "forbidden"


def test_list_requires_vendor_manager_role() -> None:
    resp = _client(_seed_vendor_repo(), EmployeeSelectionRepository()).get(
        "/vendor/me/orders", headers={"x-user-role": "employee", "x-vendor-id": "1"}
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "forbidden"


# --- detail ---

def test_get_order_returns_full_order() -> None:
    vendor_repo = _seed_vendor_repo()
    selection_repo = EmployeeSelectionRepository()
    order = selection_repo.create_order(employee_id=10, vendor_id=1, items=[], meal_date=None)

    resp = _client(vendor_repo, selection_repo).get(
        f"/vendor/me/orders/{order.id}", headers=_vh(1)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == order.id
    assert body.get("employee_id") is None
    assert body.get("employee_badge_code") is None
    assert body.get("masked_name") is None
    assert body["status"] == "pending"


def test_get_order_404_for_other_vendors_order() -> None:
    vendor_repo = _seed_vendor_repo()
    selection_repo = EmployeeSelectionRepository()
    order = selection_repo.create_order(employee_id=20, vendor_id=2, items=[], meal_date=None)

    resp = _client(vendor_repo, selection_repo).get(
        f"/vendor/me/orders/{order.id}", headers=_vh(1)
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"


def test_get_order_404_for_nonexistent_order() -> None:
    resp = _client(_seed_vendor_repo(), EmployeeSelectionRepository()).get(
        "/vendor/me/orders/9999", headers=_vh(1)
    )
    assert resp.status_code == 404


# --- status update ---

def test_patch_status_pending_to_confirmed() -> None:
    vendor_repo = _seed_vendor_repo()
    selection_repo = EmployeeSelectionRepository()
    order = selection_repo.create_order(employee_id=10, vendor_id=1, items=[], meal_date=None)

    resp = _client(vendor_repo, selection_repo).patch(
        f"/vendor/me/orders/{order.id}/status",
        headers=_vh(1),
        json={"status": "confirmed"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "confirmed"
    # regression: the PATCH status response must be de-identified like every
    # other vendor path (no internal employee uid / badge / masked name leak).
    assert body.get("employee_id") is None
    assert body.get("employee_badge_code") is None
    assert body.get("masked_name") is None


def test_patch_status_pending_to_cancelled() -> None:
    vendor_repo = _seed_vendor_repo()
    selection_repo = EmployeeSelectionRepository()
    order = selection_repo.create_order(employee_id=10, vendor_id=1, items=[], meal_date=None)

    resp = _client(vendor_repo, selection_repo).patch(
        f"/vendor/me/orders/{order.id}/status",
        headers=_vh(1),
        json={"status": "cancelled"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "cancelled"
    assert body["cancelled_at"] is not None


def test_patch_status_full_happy_path() -> None:
    vendor_repo = _seed_vendor_repo()
    selection_repo = EmployeeSelectionRepository()
    order = selection_repo.create_order(employee_id=10, vendor_id=1, items=[], meal_date=None)
    client = _client(vendor_repo, selection_repo)

    for next_status in ("confirmed", "preparing", "ready", "delivered"):
        resp = client.patch(
            f"/vendor/me/orders/{order.id}/status",
            headers=_vh(1),
            json={"status": next_status},
        )
        assert resp.status_code == 200, f"failed at transition to {next_status}"
        assert resp.json()["status"] == next_status


def test_patch_status_rejects_invalid_transition() -> None:
    vendor_repo = _seed_vendor_repo()
    selection_repo = EmployeeSelectionRepository()
    order = selection_repo.create_order(employee_id=10, vendor_id=1, items=[], meal_date=None)

    resp = _client(vendor_repo, selection_repo).patch(
        f"/vendor/me/orders/{order.id}/status",
        headers=_vh(1),
        json={"status": "delivered"},  # pending → delivered is not allowed
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "invalid_status_transition"


def test_patch_status_rejects_transition_from_terminal_state() -> None:
    vendor_repo = _seed_vendor_repo()
    selection_repo = EmployeeSelectionRepository()
    order = selection_repo.create_order(employee_id=10, vendor_id=1, items=[], meal_date=None)
    selection_repo.update_order_status(vendor_id=1, order_id=order.id, new_status="delivered")

    resp = _client(vendor_repo, selection_repo).patch(
        f"/vendor/me/orders/{order.id}/status",
        headers=_vh(1),
        json={"status": "confirmed"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "invalid_status_transition"


def test_update_status_records_audit_entry() -> None:
    vendor_repo = _seed_vendor_repo()
    selection_repo = EmployeeSelectionRepository()
    audit_repo = AuditLogRepository()
    order = selection_repo.create_order(employee_id=10, vendor_id=1, items=[], meal_date=None)

    service = VendorOrderService(selection_repo, vendor_repo, audit_repo)
    service.update_status(1, order.id, "confirmed", actor_user_id=500)

    entries = audit_repo.list(action="order.status_update")
    assert len(entries) == 1
    entry = entries[0]
    assert entry.target_type == "order"
    assert entry.target_id == order.id
    assert entry.actor_user_id == 500
    assert entry.actor_role == "vendor_manager"
    assert entry.metadata == {"from": "pending", "to": "confirmed"}


def test_patch_status_404_for_other_vendors_order() -> None:
    vendor_repo = _seed_vendor_repo()
    selection_repo = EmployeeSelectionRepository()
    order = selection_repo.create_order(employee_id=20, vendor_id=2, items=[], meal_date=None)

    resp = _client(vendor_repo, selection_repo).patch(
        f"/vendor/me/orders/{order.id}/status",
        headers=_vh(1),
        json={"status": "confirmed"},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"
