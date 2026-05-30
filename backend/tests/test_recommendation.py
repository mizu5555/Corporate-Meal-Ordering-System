"""Tests for EmployeeOrderingService.recommend() — sales-based meal recommendations."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository
from backend.repositories.menu_item_repository import MenuItemRepository
from backend.repositories.reporting_repository import ReportingRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord
from backend.services.employee_ordering_service import EmployeeOrderingService


def _make_service(
    vendor_repo: VendorProfileRepository,
    item_repo: MenuItemRepository,
    selection_repo: EmployeeSelectionRepository,
    reporting_repo: ReportingRepository,
) -> EmployeeOrderingService:
    return EmployeeOrderingService(
        vendor_repo,
        item_repo,
        selection_repo,
        AuditLogRepository(),
        reporting_repository=reporting_repo,
    )


def _base_vendor_repo() -> VendorProfileRepository:
    """Approved vendor #1, no facility restrictions (no employee_facility assignment)."""
    repo = VendorProfileRepository()
    repo.seed(
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
    return repo


def _seed_sale(
    reporting_repo: ReportingRepository,
    *,
    order_id: int,
    vendor_id: int,
    items: list[tuple[int, int, int]],
) -> None:
    """Seed a non-cancelled order into ReportingRepository within the 30-day window."""
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


# ---------------------------------------------------------------------------
# Test 1: top-selling item ranks first
# ---------------------------------------------------------------------------
def test_top_selling_item_ranks_first() -> None:
    vendor_repo = _base_vendor_repo()
    item_repo = MenuItemRepository()
    selection_repo = EmployeeSelectionRepository()
    reporting_repo = ReportingRepository()

    popular = item_repo.create(vendor_id=1, name="Popular Rice", price_cents=120, daily_quota=50)
    less_popular = item_repo.create(vendor_id=1, name="Less Popular Noodle", price_cents=100, daily_quota=50)

    # Seed sales: popular item sold 10, less popular sold 3
    _seed_sale(reporting_repo, order_id=1, vendor_id=1, items=[(popular.id, 10, 120)])
    _seed_sale(reporting_repo, order_id=2, vendor_id=1, items=[(less_popular.id, 3, 100)])

    svc = _make_service(vendor_repo, item_repo, selection_repo, reporting_repo)
    results = svc.recommend(limit=8)

    assert len(results) >= 2
    assert results[0].item.id == popular.id
    assert results[0].quantity_sold == 10
    assert results[0].from_sales is True
    assert results[1].item.id == less_popular.id
    assert results[1].quantity_sold == 3


# ---------------------------------------------------------------------------
# Test 2: unavailable item is excluded
# ---------------------------------------------------------------------------
def test_unavailable_item_excluded() -> None:
    vendor_repo = _base_vendor_repo()
    item_repo = MenuItemRepository()
    selection_repo = EmployeeSelectionRepository()
    reporting_repo = ReportingRepository()

    good = item_repo.create(vendor_id=1, name="Good Item", price_cents=100, daily_quota=10)
    hidden = item_repo.create(vendor_id=1, name="Hidden Item", price_cents=80, available=False)

    # Seed sales for both — but hidden is unavailable so should be excluded
    _seed_sale(reporting_repo, order_id=1, vendor_id=1, items=[(hidden.id, 20, 80)])
    _seed_sale(reporting_repo, order_id=2, vendor_id=1, items=[(good.id, 5, 100)])

    svc = _make_service(vendor_repo, item_repo, selection_repo, reporting_repo)
    results = svc.recommend(limit=8)

    returned_ids = [r.item.id for r in results]
    assert hidden.id not in returned_ids
    assert good.id in returned_ids


# ---------------------------------------------------------------------------
# Test 3: quota-exhausted item is excluded
# ---------------------------------------------------------------------------
def test_quota_exhausted_item_excluded() -> None:
    vendor_repo = _base_vendor_repo()
    item_repo = MenuItemRepository()
    selection_repo = EmployeeSelectionRepository()
    reporting_repo = ReportingRepository()

    today = date.today()
    quota_item = item_repo.create(vendor_id=1, name="Quota Item", price_cents=100, daily_quota=2)
    other_item = item_repo.create(vendor_id=1, name="Other Item", price_cents=90, daily_quota=10)

    # Exhaust quota for today
    from backend.repositories.employee_selection_repository import OrderItemSnapshot
    selection_repo.create_order(
        employee_id=200,
        vendor_id=1,
        meal_date=today,
        items=[OrderItemSnapshot(item_id=quota_item.id, item_name=quota_item.name, quantity=2, unit_price_cents=100)],
    )

    # Seed sales for both items
    _seed_sale(reporting_repo, order_id=1, vendor_id=1, items=[(quota_item.id, 15, 100)])
    _seed_sale(reporting_repo, order_id=2, vendor_id=1, items=[(other_item.id, 5, 90)])

    svc = _make_service(vendor_repo, item_repo, selection_repo, reporting_repo)
    results = svc.recommend(meal_date=today, limit=8)

    returned_ids = [r.item.id for r in results]
    assert quota_item.id not in returned_ids
    assert other_item.id in returned_ids


# ---------------------------------------------------------------------------
# Test 4: no sales → fallback to available items (from_sales=False)
# ---------------------------------------------------------------------------
def test_fallback_when_no_sales_data() -> None:
    vendor_repo = _base_vendor_repo()
    item_repo = MenuItemRepository()
    selection_repo = EmployeeSelectionRepository()
    reporting_repo = ReportingRepository()  # empty — no sales seeded

    item_repo.create(vendor_id=1, name="Soup", price_cents=60, daily_quota=5)
    item_repo.create(vendor_id=1, name="Rice", price_cents=80, daily_quota=5)

    svc = _make_service(vendor_repo, item_repo, selection_repo, reporting_repo)
    results = svc.recommend(limit=8)

    assert len(results) >= 1
    for r in results:
        assert r.from_sales is False
        assert r.quantity_sold == 0


# ---------------------------------------------------------------------------
# Test 5: empty vendor list returns []
# ---------------------------------------------------------------------------
def test_no_vendors_returns_empty() -> None:
    vendor_repo = VendorProfileRepository()  # no vendors seeded
    item_repo = MenuItemRepository()
    selection_repo = EmployeeSelectionRepository()
    reporting_repo = ReportingRepository()

    svc = _make_service(vendor_repo, item_repo, selection_repo, reporting_repo)
    results = svc.recommend(limit=8)

    assert results == []
