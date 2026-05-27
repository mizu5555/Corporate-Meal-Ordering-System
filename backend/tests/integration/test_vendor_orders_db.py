"""Integration tests for vendor order endpoints against a real PostgreSQL database.

Run with DATABASE_URL set:
    DATABASE_URL=postgresql://... pytest backend/tests/integration/test_vendor_orders_db.py -v
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from backend.db.connection import get_connection
from backend.main import app

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def seeded_ids():
    """Return (vendor_id, employee_id) for the rows seeded by migrations."""
    with get_connection() as conn:
        vendor = conn.execute(
            "SELECT id FROM vendors WHERE name = 'Sunny Kitchen'"
        ).fetchone()
        employee = conn.execute(
            "SELECT id FROM users WHERE email = 'employee@corpmeal.local'"
        ).fetchone()
    assert vendor is not None, "Sunny Kitchen vendor not found — did migrations run?"
    assert employee is not None, "employee@corpmeal.local not found — did migrations run?"
    return vendor["id"], employee["id"]


@pytest.fixture(autouse=True)
def clean_orders():
    """Remove orders inserted during each test so tests don't interfere."""
    yield
    with get_connection() as conn:
        conn.execute("DELETE FROM order_items")
        conn.execute("DELETE FROM orders")
        conn.execute("DELETE FROM vendors WHERE name LIKE 'IntTest%'")
        conn.commit()


def _vh(vendor_id: int) -> dict[str, str]:
    return {"x-user-role": "vendor_manager", "x-vendor-id": str(vendor_id)}


def _insert_order(vendor_id: int, employee_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "INSERT INTO orders (employee_id, vendor_id, total_price_cents) "
            "VALUES (%s, %s, 0) RETURNING id",
            (employee_id, vendor_id),
        ).fetchone()
        conn.commit()
    return row["id"]


# ---------------------------------------------------------------------------
# GET /vendor/me/orders
# ---------------------------------------------------------------------------


def test_list_orders_returns_own_orders(client, seeded_ids):
    vendor_id, employee_id = seeded_ids
    order_id = _insert_order(vendor_id, employee_id)

    resp = client.get("/vendor/me/orders", headers=_vh(vendor_id))
    assert resp.status_code == 200
    ids = [o["id"] for o in resp.json()]
    assert order_id in ids


def test_list_orders_excludes_other_vendor(client, seeded_ids):
    vendor_id, employee_id = seeded_ids

    with get_connection() as conn:
        other = conn.execute(
            "INSERT INTO vendors (name, status) VALUES ('IntTest Other', 'approved') RETURNING id"
        ).fetchone()
        conn.commit()
    _insert_order(other["id"], employee_id)

    resp = client.get("/vendor/me/orders", headers=_vh(vendor_id))
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /vendor/me/orders/{id}
# ---------------------------------------------------------------------------


def test_get_order_returns_detail(client, seeded_ids):
    vendor_id, employee_id = seeded_ids
    order_id = _insert_order(vendor_id, employee_id)

    resp = client.get(f"/vendor/me/orders/{order_id}", headers=_vh(vendor_id))
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == order_id
    assert body["status"] == "pending"
    assert "items" in body


def test_get_order_404_for_other_vendors_order(client, seeded_ids):
    vendor_id, employee_id = seeded_ids

    with get_connection() as conn:
        other = conn.execute(
            "INSERT INTO vendors (name, status) VALUES ('IntTest Other2', 'approved') RETURNING id"
        ).fetchone()
        conn.commit()
    order_id = _insert_order(other["id"], employee_id)

    resp = client.get(f"/vendor/me/orders/{order_id}", headers=_vh(vendor_id))
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"


# ---------------------------------------------------------------------------
# PATCH /vendor/me/orders/{id}/status
# ---------------------------------------------------------------------------


def test_patch_status_pending_to_confirmed_persists(client, seeded_ids):
    vendor_id, employee_id = seeded_ids
    order_id = _insert_order(vendor_id, employee_id)

    resp = client.patch(
        f"/vendor/me/orders/{order_id}/status",
        headers=_vh(vendor_id),
        json={"status": "confirmed"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"

    with get_connection() as conn:
        row = conn.execute("SELECT status FROM orders WHERE id = %s", (order_id,)).fetchone()
    assert row["status"] == "confirmed"


def test_patch_status_full_transition_chain(client, seeded_ids):
    vendor_id, employee_id = seeded_ids
    order_id = _insert_order(vendor_id, employee_id)

    for status in ("confirmed", "preparing", "ready", "delivered"):
        resp = client.patch(
            f"/vendor/me/orders/{order_id}/status",
            headers=_vh(vendor_id),
            json={"status": status},
        )
        assert resp.status_code == 200, f"failed at transition to {status}"
        assert resp.json()["status"] == status

    with get_connection() as conn:
        row = conn.execute("SELECT status FROM orders WHERE id = %s", (order_id,)).fetchone()
    assert row["status"] == "delivered"


def test_patch_status_pending_to_cancelled(client, seeded_ids):
    vendor_id, employee_id = seeded_ids
    order_id = _insert_order(vendor_id, employee_id)

    resp = client.patch(
        f"/vendor/me/orders/{order_id}/status",
        headers=_vh(vendor_id),
        json={"status": "cancelled"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "cancelled"
    assert body["cancelled_at"] is not None


def test_patch_status_invalid_transition_returns_409(client, seeded_ids):
    vendor_id, employee_id = seeded_ids
    order_id = _insert_order(vendor_id, employee_id)

    resp = client.patch(
        f"/vendor/me/orders/{order_id}/status",
        headers=_vh(vendor_id),
        json={"status": "delivered"},  # pending → delivered not allowed
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "invalid_status_transition"


def test_patch_status_terminal_state_rejects_further_transitions(client, seeded_ids):
    vendor_id, employee_id = seeded_ids
    order_id = _insert_order(vendor_id, employee_id)

    client.patch(
        f"/vendor/me/orders/{order_id}/status",
        headers=_vh(vendor_id),
        json={"status": "cancelled"},
    )

    resp = client.patch(
        f"/vendor/me/orders/{order_id}/status",
        headers=_vh(vendor_id),
        json={"status": "confirmed"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "invalid_status_transition"


def test_patch_status_404_for_other_vendors_order(client, seeded_ids):
    vendor_id, employee_id = seeded_ids

    with get_connection() as conn:
        other = conn.execute(
            "INSERT INTO vendors (name, status) VALUES ('IntTest Other3', 'approved') RETURNING id"
        ).fetchone()
        conn.commit()
    order_id = _insert_order(other["id"], employee_id)

    resp = client.patch(
        f"/vendor/me/orders/{order_id}/status",
        headers=_vh(vendor_id),
        json={"status": "confirmed"},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"
