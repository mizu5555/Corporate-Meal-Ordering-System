from datetime import date, datetime, timezone

import pytest

from backend.core.errors import CodedHTTPException
from backend.repositories.reporting_repository import ReportingRepository
from backend.schemas.admin_stats import (
    DashboardStats,
    DayPoint,
    FacilityStat,
    OrderSummary,
    VendorStat,
)
from backend.services.admin_stats_service import AdminStatsService


def test_dashboard_stats_shape():
    stats = DashboardStats(
        start=date(2026, 5, 1),
        end=date(2026, 5, 30),
        summary=OrderSummary(
            order_count=2, total_revenue_cents=3000, total_quantity=4, active_vendor_count=1
        ),
        vendor_ranking=[
            VendorStat(vendor_id=1, vendor_name="Sunny Kitchen", order_count=2, quantity=4, revenue_cents=3000)
        ],
        facility_distribution=[
            FacilityStat(facility_id=1, facility_name="Fab 12A", order_count=2, quantity=4)
        ],
        daily_trend=[DayPoint(day=date(2026, 5, 1), order_count=2, revenue_cents=3000)],
    )
    assert stats.summary.order_count == 2
    assert stats.vendor_ranking[0].vendor_name == "Sunny Kitchen"
    assert stats.facility_distribution[0].facility_id == 1
    assert stats.daily_trend[0].revenue_cents == 3000


def _service_with_one_order() -> AdminStatsService:
    repo = ReportingRepository()
    repo.seed_order(
        order_id=1, vendor_id=1, vendor_name="Sunny Kitchen",
        facility_id=1, facility_name="Fab 12A", status="delivered",
        created_at=datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc),
        items=[(10, 2, 1000)],
    )
    return AdminStatsService(reporting_repository=repo)


def test_service_assembles_dashboard():
    svc = _service_with_one_order()
    stats = svc.dashboard(date(2026, 5, 1), date(2026, 5, 31))
    assert stats.summary.order_count == 1
    assert stats.vendor_ranking[0].vendor_name == "Sunny Kitchen"
    assert stats.start == date(2026, 5, 1)
    assert stats.end == date(2026, 5, 31)


def test_service_rejects_inverted_range():
    svc = _service_with_one_order()
    with pytest.raises(CodedHTTPException) as exc:
        svc.dashboard(date(2026, 5, 31), date(2026, 5, 1))
    assert exc.value.status_code == 400
