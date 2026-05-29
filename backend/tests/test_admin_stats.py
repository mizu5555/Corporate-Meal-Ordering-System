from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.core.errors import CodedHTTPException
from backend.core.reporting import get_reporting_repository
from backend.main import app
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


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------

client = TestClient(app)


def _override_repo(repo):
    app.dependency_overrides[get_reporting_repository] = lambda: repo


def teardown_function():
    app.dependency_overrides.clear()


def test_stats_requires_admin_or_committee():
    _override_repo(ReportingRepository())
    r = client.get("/admin/stats", headers={"x-user-role": "employee"})
    assert r.status_code == 403


def test_stats_returns_payload_for_committee():
    repo = ReportingRepository()
    repo.seed_order(
        order_id=1, vendor_id=1, vendor_name="Sunny Kitchen",
        facility_id=1, facility_name="Fab 12A", status="delivered",
        created_at=datetime.now(timezone.utc), items=[(10, 2, 1000)],
    )
    _override_repo(repo)
    r = client.get("/admin/stats", headers={"x-user-role": "committee_reviewer"})
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["order_count"] == 1
    assert body["vendor_ranking"][0]["vendor_name"] == "Sunny Kitchen"


def test_stats_rejects_inverted_range():
    _override_repo(ReportingRepository())
    r = client.get("/admin/stats?start=2026-05-31&end=2026-05-01",
                   headers={"x-user-role": "admin"})
    assert r.status_code == 400
