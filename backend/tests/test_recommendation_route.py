"""Route-level tests for GET /employee/recommendations."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient

from backend.main import app
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository
from backend.repositories.menu_item_repository import MenuItemRepository
from backend.repositories.reporting_repository import ReportingRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord
from backend.routes.employee_ordering import get_employee_ordering_service
from backend.services.employee_ordering_service import EmployeeOrderingService


def _make_service_with_reporting(
    reporting_repo: ReportingRepository,
) -> EmployeeOrderingService:
    vendor_repo = VendorProfileRepository()
    vendor_repo.seed(
        VendorRecord(
            id=1,
            name="Sunny Kitchen",
            status="approved",
            address="No. 10",
            business_hours="11:00-14:00",
            contact_phone="0912-000-001",
            contact_email="sunny@example.com",
        )
    )
    item_repo = MenuItemRepository()
    selection_repo = EmployeeSelectionRepository()
    return EmployeeOrderingService(
        vendor_repo,
        item_repo,
        selection_repo,
        AuditLogRepository(),
        reporting_repository=reporting_repo,
    ), item_repo


def _seed_sale(
    reporting_repo: ReportingRepository,
    *,
    order_id: int,
    vendor_id: int,
    items: list[tuple[int, int, int]],
) -> None:
    """Seed a delivered order into ReportingRepository within the 30-day window."""
    reporting_repo.seed_order(
        order_id=order_id,
        vendor_id=vendor_id,
        vendor_name="Sunny Kitchen",
        facility_id=None,
        facility_name=None,
        status="delivered",
        created_at=datetime.combine(date.today() - timedelta(days=1), datetime.min.time()),
        items=items,
    )


def _h(user_id: int = 100) -> dict[str, str]:
    """Employee auth headers."""
    return {"x-user-role": "employee", "x-user-id": str(user_id)}


def teardown_function() -> None:
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 1: non-employee caller is blocked (403)
# ---------------------------------------------------------------------------
def test_recommendations_requires_employee_role() -> None:
    reporting_repo = ReportingRepository()
    svc, _ = _make_service_with_reporting(reporting_repo)
    app.dependency_overrides[get_employee_ordering_service] = lambda: svc

    client = TestClient(app)
    resp = client.get("/employee/recommendations", headers={"x-user-role": "vendor_manager"})

    assert resp.status_code == 403
    assert resp.json()["code"] == "forbidden"


# ---------------------------------------------------------------------------
# Test 2: unauthenticated caller is blocked (400 — missing x-user-id)
# ---------------------------------------------------------------------------
def test_recommendations_requires_user_id_header() -> None:
    reporting_repo = ReportingRepository()
    svc, _ = _make_service_with_reporting(reporting_repo)
    app.dependency_overrides[get_employee_ordering_service] = lambda: svc

    client = TestClient(app)
    # role is correct but no x-user-id → require_employee raises 400
    resp = client.get("/employee/recommendations", headers={"x-user-role": "employee"})

    assert resp.status_code == 400
    assert resp.json()["code"] == "validation_error"


# ---------------------------------------------------------------------------
# Test 3: employee gets 200 with a list, top-selling item first
# ---------------------------------------------------------------------------
def test_recommendations_returns_top_seller_first() -> None:
    reporting_repo = ReportingRepository()
    svc, item_repo = _make_service_with_reporting(reporting_repo)

    popular = item_repo.create(vendor_id=1, name="Popular Rice", price_cents=120, daily_quota=50)
    less_popular = item_repo.create(vendor_id=1, name="Less Popular Noodle", price_cents=100, daily_quota=50)

    _seed_sale(reporting_repo, order_id=1, vendor_id=1, items=[(popular.id, 10, 120)])
    _seed_sale(reporting_repo, order_id=2, vendor_id=1, items=[(less_popular.id, 3, 100)])

    app.dependency_overrides[get_employee_ordering_service] = lambda: svc
    client = TestClient(app)

    resp = client.get("/employee/recommendations", headers=_h(100))

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 2
    assert body[0]["item"]["id"] == popular.id
    assert body[0]["quantity_sold"] == 10
    assert body[1]["item"]["id"] == less_popular.id
    assert body[1]["quantity_sold"] == 3


# ---------------------------------------------------------------------------
# Test 4: each item in the response has the from_sales field
# ---------------------------------------------------------------------------
def test_recommendations_items_have_from_sales_field() -> None:
    reporting_repo = ReportingRepository()
    svc, item_repo = _make_service_with_reporting(reporting_repo)

    item = item_repo.create(vendor_id=1, name="Rice Bowl", price_cents=120, daily_quota=10)
    _seed_sale(reporting_repo, order_id=1, vendor_id=1, items=[(item.id, 5, 120)])

    app.dependency_overrides[get_employee_ordering_service] = lambda: svc
    client = TestClient(app)

    resp = client.get("/employee/recommendations", headers=_h(100))

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 1
    for rec in body:
        assert "from_sales" in rec
    assert body[0]["from_sales"] is True
