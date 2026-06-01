"""Integration test: employee onboarding flow against a real PostgreSQL database.

Flow: register → is_active=False → login blocked → admin enables → login works → employee routes work.

    DATABASE_URL=postgresql://... pytest backend/tests/integration/test_employee_onboarding_db.py -v
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


@pytest.fixture(scope="module")
def admin_headers():
    """JWT for the seeded admin account."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE email = 'admin@corpmeal.local'"
        ).fetchone()
    assert row, "admin@corpmeal.local not found — did migrations run?"
    token = create_access_token({"sub": str(row["id"]), "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def registered_employee(client):
    """Register a new employee and yield their (user_id, jwt_headers). Clean up after test."""
    resp = client.post(
        "/auth/register",
        json={
            "email": "onboarding.test@corpmeal.local",
            "password": "testpass123",
            "display_name": "Onboarding Test",
            "role": "employee",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    user_id = body["user_id"]
    token = body["access_token"]

    yield user_id, {"Authorization": f"Bearer {token}"}

    with get_connection() as conn:
        conn.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_employee_register_returns_is_active_false(client):
    """Newly registered employee should have is_active=False in the response."""
    resp = client.post(
        "/auth/register",
        json={
            "email": "onboarding.check@corpmeal.local",
            "password": "testpass123",
            "display_name": "Check User",
            "role": "employee",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["is_active"] is False

    # cleanup
    with get_connection() as conn:
        conn.execute("DELETE FROM users WHERE id = %s", (body["user_id"],))
        conn.commit()


# ---------------------------------------------------------------------------
# Pre-approval: employee is blocked
# ---------------------------------------------------------------------------


def test_pending_employee_login_is_blocked(client, registered_employee):
    user_id, _ = registered_employee
    resp = client.post(
        "/auth/login",
        json={"email": "onboarding.test@corpmeal.local", "password": "testpass123"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "account_disabled"


def test_pending_employee_cannot_browse_vendors(client, registered_employee):
    _, headers = registered_employee
    resp = client.get("/employee/vendors", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["code"] == "account_disabled"


# ---------------------------------------------------------------------------
# Admin approves the employee
# ---------------------------------------------------------------------------


def test_admin_can_see_pending_employee(client, admin_headers, registered_employee):
    user_id, _ = registered_employee
    resp = client.get("/admin/users?role=employee&is_active=false", headers=admin_headers)
    assert resp.status_code == 200
    ids = [u["id"] for u in resp.json()["users"]]
    assert user_id in ids


def test_full_onboarding_flow(client, admin_headers, registered_employee):
    """register → blocked → admin enables → can login and browse."""
    user_id, headers = registered_employee

    # Step 1: blocked before approval
    resp = client.get("/employee/vendors", headers=headers)
    assert resp.status_code == 403

    # Step 2: admin enables
    resp = client.patch(f"/admin/users/{user_id}/enable", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True

    # Step 3: employee can now login
    resp = client.post(
        "/auth/login",
        json={"email": "onboarding.test@corpmeal.local", "password": "testpass123"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True

    # Step 4: employee can access ordering routes
    new_token = resp.json()["access_token"]
    resp = client.get("/employee/vendors", headers={"Authorization": f"Bearer {new_token}"})
    assert resp.status_code == 200
