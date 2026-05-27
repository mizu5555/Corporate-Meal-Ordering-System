"""Integration test: atomic quota deduction under concurrent load.

Requires a live PostgreSQL instance (DATABASE_URL env var).
Skipped automatically in CI without a database.

Scenario
--------
A menu item has daily_quota = 1.
N threads each try to create an order for that item simultaneously.
Expected outcome: exactly 1 succeeds (HTTP 201), the rest get 409 quota_exhausted.
"""
from __future__ import annotations

import os
import threading
from datetime import date

import pytest

DATABASE_URL = os.getenv("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set — skipping integration test",
)


@pytest.fixture(scope="module")
def db_conn():
    """Run migrations, then open a raw psycopg connection for test setup/teardown."""
    from psycopg import connect
    from psycopg.rows import dict_row
    from backend.db.migrate import run_migrations

    run_migrations()

    conn = connect(DATABASE_URL, row_factory=dict_row, autocommit=True)
    yield conn
    conn.close()


@pytest.fixture()
def quota_item(db_conn):
    """Create a vendor, menu item (quota=1), and employee; clean up after test."""
    cur = db_conn.cursor()

    # Vendor
    cur.execute(
        """
        INSERT INTO vendors (name, status, contact_email)
        VALUES ('Quota Test Kitchen', 'approved', 'quotatest@example.com')
        RETURNING id
        """
    )
    vendor_id = cur.fetchone()["id"]

    # Menu item with quota = 1
    cur.execute(
        """
        INSERT INTO menu_items (vendor_id, name, price_cents, available, daily_quota)
        VALUES (%s, 'Last Bento', 500, TRUE, 1)
        RETURNING id
        """,
        (vendor_id,),
    )
    item_id = cur.fetchone()["id"]

    # Employee user
    cur.execute(
        """
        INSERT INTO users (email, display_name, role_id)
        SELECT 'quotatest@example.com', 'Quota Tester',
               (SELECT id FROM roles WHERE name = 'employee')
        RETURNING id
        """
    )
    employee_id = cur.fetchone()["id"]

    yield {"vendor_id": vendor_id, "item_id": item_id, "employee_id": employee_id}

    # Teardown
    cur.execute("DELETE FROM order_items WHERE item_id = %s", (item_id,))
    cur.execute(
        "DELETE FROM orders WHERE vendor_id = %s AND employee_id = %s",
        (vendor_id, employee_id),
    )
    cur.execute("DELETE FROM menu_items WHERE id = %s", (item_id,))
    cur.execute("DELETE FROM vendors WHERE id = %s", (vendor_id,))
    cur.execute("DELETE FROM users WHERE id = %s", (employee_id,))


def test_concurrent_orders_no_oversell(quota_item) -> None:
    """N concurrent requests on quota=1 item → exactly 1 success, rest 409."""
    from backend.repositories.employee_selection_repository import OrderItemSnapshot
    from backend.repositories.postgres_employee_selection_repository import (
        PostgresEmployeeSelectionRepository,
    )
    from backend.core.errors import CodedHTTPException

    CONCURRENCY = 8
    meal_date = date.today()
    item_snap = OrderItemSnapshot(
        item_id=quota_item["item_id"],
        item_name="Last Bento",
        quantity=1,
        unit_price_cents=500,
    )

    successes: list[int] = []
    failures: list[str] = []
    lock = threading.Lock()

    def try_order() -> None:
        repo = PostgresEmployeeSelectionRepository()
        try:
            order = repo.create_order(
                employee_id=quota_item["employee_id"],
                vendor_id=quota_item["vendor_id"],
                items=[item_snap],
                meal_date=meal_date,
            )
            with lock:
                successes.append(order.id)
        except CodedHTTPException as exc:
            with lock:
                failures.append(exc.code)
        except Exception as exc:
            with lock:
                failures.append(str(exc))

    threads = [threading.Thread(target=try_order) for _ in range(CONCURRENCY)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(successes) == 1, (
        f"Expected exactly 1 successful order, got {len(successes)}: {successes}"
    )
    assert len(failures) == CONCURRENCY - 1, (
        f"Expected {CONCURRENCY - 1} failures, got {len(failures)}: {failures}"
    )
    # After the winning thread commits, the item is auto-marked available=FALSE
    # (issue #53). Threads that checked *before* the commit see quota_exhausted;
    # threads that checked *after* see item_unavailable. Both are correct — no
    # oversell occurred either way.
    valid_rejection_codes = {"quota_exhausted", "item_unavailable"}
    unexpected = [f for f in failures if f not in valid_rejection_codes]
    assert not unexpected, (
        f"All failures should be quota_exhausted or item_unavailable, got unexpected: {unexpected}"
    )
