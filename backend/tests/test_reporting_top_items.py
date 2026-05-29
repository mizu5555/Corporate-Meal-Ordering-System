from datetime import date, datetime, timezone

from backend.repositories.reporting_repository import ReportingRepository

W_START = date(2026, 5, 1)
W_END = date(2026, 5, 31)


def _ts(day):
    return datetime(2026, 5, day, 12, 0, tzinfo=timezone.utc)


def _seed(repo):
    repo.seed_order(order_id=1, vendor_id=1, vendor_name="Sunny", facility_id=1,
                    facility_name="F12A", status="delivered", created_at=_ts(1),
                    items=[(10, 5, 500), (11, 1, 900)])
    repo.seed_order(order_id=2, vendor_id=1, vendor_name="Sunny", facility_id=1,
                    facility_name="F12A", status="pending", created_at=_ts(2),
                    items=[(10, 2, 500)])
    repo.seed_order(order_id=3, vendor_id=2, vendor_name="Noodle", facility_id=2,
                    facility_name="F14B", status="cancelled", created_at=_ts(2),
                    items=[(20, 9, 900)])


def test_top_items_ranks_by_quantity_excludes_cancelled():
    repo = ReportingRepository()
    _seed(repo)
    rows = repo.top_items(W_START, W_END, limit=10)
    assert [(r.item_id, r.quantity_sold) for r in rows] == [(10, 7), (11, 1)]
    assert rows[0].vendor_id == 1


def test_top_items_vendor_filter_and_limit():
    repo = ReportingRepository()
    _seed(repo)
    rows = repo.top_items(W_START, W_END, limit=1, vendor_ids=[1])
    assert len(rows) == 1 and rows[0].item_id == 10
