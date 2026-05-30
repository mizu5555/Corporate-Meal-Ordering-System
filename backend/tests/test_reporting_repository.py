from datetime import date, datetime, timezone

from backend.repositories.reporting_repository import ReportingRepository

W_START = date(2026, 5, 1)
W_END = date(2026, 5, 31)


def _ts(day: int) -> datetime:
    return datetime(2026, 5, day, 12, 0, tzinfo=timezone.utc)


def _seed(repo: ReportingRepository) -> None:
    repo.seed_order(
        order_id=1, vendor_id=1, vendor_name="Sunny Kitchen",
        facility_id=1, facility_name="Fab 12A", status="delivered",
        created_at=_ts(1), items=[(10, 2, 500), (11, 1, 1000)],
    )
    repo.seed_order(
        order_id=2, vendor_id=1, vendor_name="Sunny Kitchen",
        facility_id=1, facility_name="Fab 12A", status="pending",
        created_at=_ts(2), items=[(10, 1, 500)],
    )
    repo.seed_order(
        order_id=3, vendor_id=2, vendor_name="Noodle Bar",
        facility_id=2, facility_name="Fab 14B", status="cancelled",
        created_at=_ts(2), items=[(20, 5, 900)],
    )


def test_order_summary_excludes_cancelled():
    repo = ReportingRepository()
    _seed(repo)
    s = repo.order_summary(W_START, W_END)
    assert s.order_count == 2
    assert s.total_quantity == 4
    assert s.total_revenue_cents == 2500
    assert s.active_vendor_count == 1


def test_vendor_ranking():
    repo = ReportingRepository()
    _seed(repo)
    ranking = repo.vendor_ranking(W_START, W_END, limit=10)
    assert len(ranking) == 1
    assert ranking[0].vendor_id == 1
    assert ranking[0].order_count == 2
    assert ranking[0].quantity == 4
    assert ranking[0].revenue_cents == 2500


def test_facility_distribution():
    repo = ReportingRepository()
    _seed(repo)
    dist = repo.facility_distribution(W_START, W_END)
    assert len(dist) == 1
    assert dist[0].facility_id == 1
    assert dist[0].quantity == 4


def test_daily_trend_sorted():
    repo = ReportingRepository()
    _seed(repo)
    trend = repo.daily_trend(W_START, W_END)
    assert [p.day for p in trend] == [date(2026, 5, 1), date(2026, 5, 2)]
    assert trend[0].revenue_cents == 2000
    assert trend[1].revenue_cents == 500


def test_window_excludes_out_of_range():
    repo = ReportingRepository()
    _seed(repo)
    s = repo.order_summary(date(2026, 6, 1), date(2026, 6, 30))
    assert s.order_count == 0
    assert s.total_revenue_cents == 0
