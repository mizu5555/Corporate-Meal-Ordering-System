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
    cur.execute(
        "INSERT INTO vendors (name, status, contact_email) "
        "VALUES ('Billing Kitchen', 'approved', 'bill@example.com') RETURNING id"
    )
    vendor_id = cur.fetchone()["id"]

    def make_order(status, meal_day, qty, total):
        cur.execute(
            "INSERT INTO orders (employee_id, vendor_id, status, total_price_cents, meal_date) "
            "VALUES (1, %s, %s, %s, %s) RETURNING id",
            (vendor_id, status, total, f"2026-05-{meal_day:02d}"),
        )
        oid = cur.fetchone()["id"]
        cur.execute(
            "INSERT INTO order_items (order_id, item_name, quantity, unit_price_cents, total_price_cents) "
            "VALUES (%s, 'Box', %s, %s, %s)",
            (oid, qty, total // qty, total),
        )
        return oid

    ids = [make_order("delivered", 3, 2, 1000), make_order("pending", 4, 1, 500)]
    cur.execute(
        "INSERT INTO orders (employee_id, vendor_id, status, total_price_cents, meal_date) "
        "VALUES (1, %s, 'delivered', 700, '2026-06-01') RETURNING id",
        (vendor_id,),
    )
    jid = cur.fetchone()["id"]
    cur.execute(
        "INSERT INTO order_items (order_id, item_name, quantity, unit_price_cents, total_price_cents) "
        "VALUES (%s, 'Box', 1, 700, 700)",
        (jid,),
    )
    ids.append(jid)
    yield {"vendor_id": vendor_id, "order_ids": ids}
    cur.execute("DELETE FROM order_items WHERE order_id = ANY(%s)", (ids,))
    cur.execute("DELETE FROM orders WHERE id = ANY(%s)", (ids,))
    cur.execute("DELETE FROM vendors WHERE id = %s", (vendor_id,))
    conn.close()


def test_vendor_and_employee_monthly_delivered_only(seeded):
    from backend.repositories.postgres_reporting_repository import PostgresReportingRepository

    repo = PostgresReportingRepository()
    vrows = repo.vendor_monthly_receivables(2026, 5)
    mine = [v for v in vrows if v.vendor_id == seeded["vendor_id"]][0]
    assert mine.amount_cents == 1000
    assert mine.order_count == 1

    erows = repo.employee_monthly_totals(2026, 5)
    emp = [e for e in erows if e.employee_id == 1][0]
    assert emp.amount_cents == 1000
