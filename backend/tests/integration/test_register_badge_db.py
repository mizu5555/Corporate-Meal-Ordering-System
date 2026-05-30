"""Registration assigns an EMP-NNNN badge to employees (not to vendor managers)."""
import os
import uuid

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


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def test_employee_registration_assigns_badge(client):
    email = _unique_email("emp")
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": "Reg Tester", "role": "employee"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["badge_code"] is not None
    assert body["badge_code"].startswith("EMP-")
    with get_connection() as conn:
        row = conn.execute("SELECT badge_code FROM users WHERE email = %s", (email,)).fetchone()
    assert row["badge_code"] == body["badge_code"]


def test_vendor_manager_registration_has_no_badge(client):
    email = _unique_email("vm")
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": "VM Tester", "role": "vendor_manager"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["badge_code"] is None
