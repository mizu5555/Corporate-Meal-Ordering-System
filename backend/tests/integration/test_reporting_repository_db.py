import os
from datetime import date

import pytest

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="requires DATABASE_URL")

DATABASE_URL = os.getenv("DATABASE_URL", "")


@pytest.fixture()
def seeded(tmp_path):
    from psycopg import connect
    from psycopg.rows import dict_row
    from backend.db.migrate import run_migrations

    run_migrations()
    conn = connect(DATABASE_URL, row_factory=dict_row, autocommit=True)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO vendors (name, status, contact_email) "
        "VALUES ('Stats Kitchen', 'approved', 'stats@example.com') RETURNING id"
    )
    vendor_id = cur.fetchone()["id"]
    cur.execute("INSERT INTO facilities (code, name) VALUES ('SREP', 'Stats Fab') "
                "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id")
    facility_id = cur.fetchone()["id"]

    def make_order(status, created_day, qty, total):
        cur.execute(
            "INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, created_at) "
            "VALUES (1, %s, %s, %s, %s, %s) RETURNING id",
            (vendor_id, facility_id, status, total, f"2026-05-{created_day:02d} 12:00+00"),
        )
        oid = cur.fetchone()["id"]
        cur.execute(
            "INSERT INTO order_items (order_id, item_name, quantity, unit_price_cents, total_price_cents) "
            "VALUES (%s, 'Box', %s, %s, %s)",
            (oid, qty, total // qty, total),
        )
        return oid

    ids = [
        make_order("delivered", 1, 2, 1000),
        make_order("pending", 2, 1, 500),
        make_order("cancelled", 2, 5, 5000),
    ]
    yield {"vendor_id": vendor_id, "facility_id": facility_id, "order_ids": ids}
    cur.execute("DELETE FROM order_items WHERE order_id = ANY(%s)", (ids,))
    cur.execute("DELETE FROM orders WHERE id = ANY(%s)", (ids,))
    cur.execute("DELETE FROM vendors WHERE id = %s", (vendor_id,))
    conn.close()


def test_summary_and_ranking_exclude_cancelled(seeded):
    from backend.repositories.postgres_reporting_repository import PostgresReportingRepository

    repo = PostgresReportingRepository()
    start, end = date(2026, 5, 1), date(2026, 5, 31)

    s = repo.order_summary(start, end)
    assert s.order_count >= 2
    assert s.total_quantity >= 3

    ranking = repo.vendor_ranking(start, end, limit=50)
    mine = [v for v in ranking if v.vendor_id == seeded["vendor_id"]][0]
    assert mine.order_count == 2
    assert mine.quantity == 3
    assert mine.revenue_cents == 1500

    dist = repo.facility_distribution(start, end)
    assert any(f.facility_id == seeded["facility_id"] and f.quantity == 3 for f in dist)

    trend = repo.daily_trend(start, end)
    assert {p.day for p in trend} >= {date(2026, 5, 1), date(2026, 5, 2)}
