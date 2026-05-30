"""E2E (real Postgres): employee badge -> vendor by-badge lookup -> pickup-confirm.

Covers the new cross-role chain end to end plus de-identification: vendor responses
expose badge + masked name, never the internal uid.
"""
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
    today = date.today()
    with get_connection() as conn:
        v1 = conn.execute("SELECT id FROM vendors WHERE name = 'Sunny Kitchen'").fetchone()["id"]
        v2 = conn.execute(
            "INSERT INTO vendors (name, status) VALUES ('BadgeTest Store2', 'approved') RETURNING id"
        ).fetchone()["id"]

        def mk_emp(email, name, badge):
            return conn.execute(
                """
                INSERT INTO users (email, display_name, role_id, password_hash, badge_code)
                SELECT %s, %s, r.id, 'x', %s FROM roles r WHERE r.name='employee'
                RETURNING id
                """,
                (email, name, badge),
            ).fetchone()["id"]

        e1 = mk_emp("badge.e1@example.com", "王小明", "BT-0001")
        e2 = mk_emp("badge.e2@example.com", "John Smith", "BT-0002")
        e3 = mk_emp("badge.e3@example.com", "李大華", "BT-0003")

        def mk_item(vendor):
            return conn.execute(
                "INSERT INTO menu_items (vendor_id, name, price_cents, available) "
                "VALUES (%s, 'BadgeTest Box', 1000, TRUE) RETURNING id",
                (vendor,),
            ).fetchone()["id"]

        item_v1 = mk_item(v1)
        item_v2 = mk_item(v2)

        def mk_ready_order(emp, vendor, item):
            oid = conn.execute(
                "INSERT INTO orders (employee_id, vendor_id, status, total_price_cents, meal_date) "
                "VALUES (%s, %s, 'ready', 1000, %s) RETURNING id",
                (emp, vendor, today),
            ).fetchone()["id"]
            conn.execute(
                "INSERT INTO order_items "
                "(order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents) "
                "VALUES (%s, %s, 'Box', 1, 1000, 1000)",
                (oid, item),
            )
            return oid

        o1 = mk_ready_order(e1, v1, item_v1)
        mk_ready_order(e2, v1, item_v1)
        mk_ready_order(e3, v2, item_v2)
        conn.commit()
    ids = {"v1": v1, "v2": v2, "e1": e1, "o1": o1}
    yield ids
    with get_connection() as conn:
        conn.execute("DELETE FROM order_items")
        conn.execute("DELETE FROM orders")
        conn.execute("DELETE FROM menu_items WHERE name = 'BadgeTest Box'")
        conn.execute("DELETE FROM users WHERE email LIKE 'badge.e%@example.com'")
        conn.execute("DELETE FROM vendors WHERE name = 'BadgeTest Store2'")
        conn.commit()


def _vendor(vendor_id):
    return {"x-user-role": "vendor_manager", "x-vendor-id": str(vendor_id)}


def _emp(uid):
    return {"x-user-role": "employee", "x-user-id": str(uid)}


def test_badge_pickup_end_to_end(client, seeded):
    badge = client.get("/employee/me/badge", headers=_emp(seeded["e1"]))
    assert badge.status_code == 200, badge.text
    assert badge.json()["badge_code"] == "BT-0001"

    lookup = client.get("/vendor/me/orders/by-badge/BT-0001", headers=_vendor(seeded["v1"]))
    assert lookup.status_code == 200, lookup.text
    body = lookup.json()
    assert [o["id"] for o in body] == [seeded["o1"]]
    assert body[0]["employee_badge_code"] == "BT-0001"
    assert body[0]["masked_name"] == "王*明"
    assert body[0].get("employee_id") is None

    confirm = client.post(
        f"/vendor/me/orders/{seeded['o1']}/pickup-confirm", headers=_vendor(seeded["v1"])
    )
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["status"] == "delivered"
    assert confirm.json().get("employee_id") is None

    other = client.get("/vendor/me/orders/by-badge/BT-0003", headers=_vendor(seeded["v1"]))
    assert other.status_code == 200
    assert other.json() == []
