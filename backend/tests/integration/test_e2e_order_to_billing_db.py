"""End-to-end integration test: employee order -> vendor fulfilment -> billing receivable.

Exercises the full cross-module chain against a real PostgreSQL database:

  1. an employee creates an order through the employee API,
  2. the vendor advances it ``pending -> confirmed -> preparing -> ready -> delivered``
     through the vendor API,
  3. the delivered order is reflected in the admin monthly receivables report.

The individual stages are covered elsewhere (``test_vendor_orders_db.py`` for status
transitions, ``test_reporting_repository_billing_db.py`` for aggregation); this test is
the cross-module hand-off none of those exercise.

Run with DATABASE_URL set, e.g.:
    DATABASE_URL=postgresql://... pytest backend/tests/integration/test_e2e_order_to_billing_db.py -v
"""
from __future__ import annotations

import os
from datetime import date

import pytest
from fastapi.testclient import TestClient

from backend.db.connection import get_connection
from backend.main import app

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def seeded():
    """Resolve the migration-seeded vendor/employee and add a fresh, available menu item."""
    with get_connection() as conn:
        vendor = conn.execute(
            "SELECT id FROM vendors WHERE name = 'Sunny Kitchen'"
        ).fetchone()
        employee = conn.execute(
            "SELECT id FROM users WHERE email = 'employee@corpmeal.local'"
        ).fetchone()
        assert vendor is not None, "Sunny Kitchen not seeded — did migrations run?"
        assert employee is not None, "employee@corpmeal.local not seeded — did migrations run?"
        item = conn.execute(
            """
            INSERT INTO menu_items (vendor_id, name, price_cents, available)
            VALUES (%s, 'E2E Bento', 1000, TRUE)
            RETURNING id
            """,
            (vendor["id"],),
        ).fetchone()
        conn.commit()
        ids = {
            "vendor_id": vendor["id"],
            "employee_id": employee["id"],
            "item_id": item["id"],
        }
    yield ids
    # Remove rows created during the test so reruns stay deterministic.
    with get_connection() as conn:
        conn.execute("DELETE FROM order_items")
        conn.execute("DELETE FROM orders")
        conn.execute("DELETE FROM menu_items WHERE id = %s", (ids["item_id"],))
        conn.commit()


def _emp_headers(employee_id: int) -> dict[str, str]:
    return {"x-user-role": "employee", "x-user-id": str(employee_id)}


def _vendor_headers(vendor_id: int) -> dict[str, str]:
    return {"x-user-role": "vendor_manager", "x-vendor-id": str(vendor_id)}


def test_order_flows_through_to_monthly_billing(client, seeded):
    today = date.today()

    # 1. employee creates an order for today (inside the 7-day pre-order window)
    create = client.post(
        f"/employee/vendors/{seeded['vendor_id']}/orders",
        headers=_emp_headers(seeded["employee_id"]),
        json={
            "items": [{"item_id": seeded["item_id"], "quantity": 2}],
            "meal_date": today.isoformat(),
        },
    )
    assert create.status_code == 201, create.text
    order = create.json()
    order_id = order["id"]
    assert order["status"] == "pending"
    assert order["total_price_cents"] == 2000

    # 2. vendor advances the order all the way to delivered
    for next_status in ("confirmed", "preparing", "ready", "delivered"):
        resp = client.patch(
            f"/vendor/me/orders/{order_id}/status",
            headers=_vendor_headers(seeded["vendor_id"]),
            json={"status": next_status},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == next_status

    # 3. the delivered order surfaces in the month's vendor receivables
    receivables = client.get(
        "/admin/billing/vendors",
        headers={"x-user-role": "admin"},
        params={"year": today.year, "month": today.month},
    )
    assert receivables.status_code == 200, receivables.text
    mine = [r for r in receivables.json() if r["vendor_id"] == seeded["vendor_id"]]
    assert mine, "delivered order did not appear in vendor receivables"
    assert mine[0]["amount_cents"] >= 2000
