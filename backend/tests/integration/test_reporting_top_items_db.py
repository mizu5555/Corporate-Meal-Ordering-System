import os
from datetime import date

import pytest

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="requires DATABASE_URL")
DATABASE_URL = os.getenv("DATABASE_URL", "")


@pytest.fixture()
def seeded():
    from psycopg import connect
    from psycopg.rows import dict_row
    from backend.db.migrate import run_migrations
    run_migrations()
    conn = connect(DATABASE_URL, row_factory=dict_row, autocommit=True)
    cur = conn.cursor()
    cur.execute("INSERT INTO vendors (name, status, contact_email) "
                "VALUES ('Reco Kitchen','approved','reco@example.com') RETURNING id")
    vid = cur.fetchone()["id"]

    # Create two menu items so FK is satisfied
    cur.execute("INSERT INTO menu_items (vendor_id, name, price_cents) VALUES (%s, 'Item A', 100) RETURNING id", (vid,))
    item_a = cur.fetchone()["id"]
    cur.execute("INSERT INTO menu_items (vendor_id, name, price_cents) VALUES (%s, 'Item B', 100) RETURNING id", (vid,))
    item_b = cur.fetchone()["id"]

    def order(status, day, item_id, qty):
        cur.execute("INSERT INTO orders (employee_id, vendor_id, status, total_price_cents, created_at) "
                    "VALUES (1,%s,%s,100,%s) RETURNING id", (vid, status, f"2026-05-{day:02d} 12:00+00"))
        oid = cur.fetchone()["id"]
        cur.execute("INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents) "
                    "VALUES (%s,%s,'X',%s,100,100)", (oid, item_id, qty))
        return oid

    ids = [order("delivered", 3, item_a, 4), order("delivered", 4, item_a, 1), order("cancelled", 4, item_b, 9)]
    yield {"vendor_id": vid, "order_ids": ids, "item_id": item_a, "item_b": item_b}
    cur.execute("DELETE FROM order_items WHERE order_id = ANY(%s)", (ids,))
    cur.execute("DELETE FROM orders WHERE id = ANY(%s)", (ids,))
    cur.execute("DELETE FROM menu_items WHERE id = ANY(%s)", ([item_a, item_b],))
    cur.execute("DELETE FROM vendors WHERE id = %s", (vid,))
    conn.close()


def test_top_items_db(seeded):
    from backend.repositories.postgres_reporting_repository import PostgresReportingRepository
    repo = PostgresReportingRepository()
    rows = repo.top_items(date(2026, 5, 1), date(2026, 5, 31), limit=50, vendor_ids=[seeded["vendor_id"]])
    mine = [r for r in rows if r.item_id == seeded["item_id"]][0]
    assert mine.quantity_sold == 5
    assert mine.vendor_id == seeded["vendor_id"]
    assert all(r.item_id != seeded["item_b"] for r in rows)
