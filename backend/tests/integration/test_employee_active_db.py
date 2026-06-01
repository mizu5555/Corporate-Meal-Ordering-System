"""Integration test: disabled employee is rejected by /employee/* endpoints.

Requires a live PostgreSQL database (DATABASE_URL env var).

    DATABASE_URL=postgresql://... pytest backend/tests/integration/test_employee_active_db.py -v
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from backend.core.security import create_access_token, hash_password
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
def disabled_employee_id():
    """Insert a disabled employee, yield their id, then clean up."""
    with get_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO users (email, display_name, role_id, password_hash, is_active)
            SELECT 'disabled.emp@test.local', 'Disabled Emp', r.id, %s, FALSE
            FROM roles r WHERE r.name = 'employee'
            RETURNING id
            """,
            (hash_password("testpass123"),),
        ).fetchone()
        conn.commit()
        user_id = row["id"]

    yield user_id

    with get_connection() as conn:
        conn.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()


@pytest.fixture()
def active_employee_id():
    """Insert an active employee, yield their id, then clean up."""
    with get_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO users (email, display_name, role_id, password_hash, is_active)
            SELECT 'active.emp@test.local', 'Active Emp', r.id, %s, TRUE
            FROM roles r WHERE r.name = 'employee'
            RETURNING id
            """,
            (hash_password("testpass123"),),
        ).fetchone()
        conn.commit()
        user_id = row["id"]

    yield user_id

    with get_connection() as conn:
        conn.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()


def _jwt_headers(user_id: int) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id), "role": "employee"})
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Disabled employee is rejected
# ---------------------------------------------------------------------------


def test_disabled_employee_cannot_browse_vendors(client, disabled_employee_id):
    resp = client.get("/employee/vendors", headers=_jwt_headers(disabled_employee_id))

    assert resp.status_code == 403
    body = resp.json()
    assert body["code"] == "account_disabled"


def test_disabled_employee_cannot_place_order(client, disabled_employee_id):
    resp = client.post(
        "/employee/vendors/1/orders",
        json={"meal_date": "2099-01-01", "items": [{"menu_item_id": 1, "quantity": 1}]},
        headers=_jwt_headers(disabled_employee_id),
    )

    assert resp.status_code == 403
    assert resp.json()["code"] == "account_disabled"


# ---------------------------------------------------------------------------
# Active employee still works (regression guard)
# ---------------------------------------------------------------------------


def test_active_employee_can_browse_vendors(client, active_employee_id):
    resp = client.get("/employee/vendors", headers=_jwt_headers(active_employee_id))

    # 200 OK (list may be empty in test DB — that's fine)
    assert resp.status_code == 200
