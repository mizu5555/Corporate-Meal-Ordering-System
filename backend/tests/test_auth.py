"""Unit tests for /auth/login and /auth/register endpoints."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.core.security import decode_access_token, hash_password
from backend.main import app

client = TestClient(app)

_PASSWORD = "password123"


def _user(role: str = "employee", vendor_id: int | None = None, is_active: bool = True) -> dict:
    return {
        "id": 1,
        "email": "user@example.com",
        "display_name": "Test User",
        "password_hash": hash_password(_PASSWORD),
        "is_active": is_active,
        "role": role,
        "vendor_id": vendor_id,
    }


def _conn_ctx(*, existing_row=None, badge_code: str | None = None) -> MagicMock:
    """Return a mock context manager for get_connection().

    First conn.execute() → SELECT check (returns existing_row or None).
    Second conn.execute() → INSERT RETURNING id, badge_code.
    """
    conn = MagicMock()
    check = MagicMock()
    check.fetchone.return_value = existing_row
    insert = MagicMock()
    insert.fetchone.return_value = {"id": 1, "badge_code": badge_code}
    conn.execute.side_effect = [check, insert]

    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def test_login_valid_credentials_returns_200_with_token() -> None:
    with patch("backend.routes.auth._fetch_user", return_value=_user()):
        resp = client.post("/auth/login", json={"email": "user@example.com", "password": _PASSWORD})

    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["role"] == "employee"
    assert body["user_id"] == 1
    assert body["token_type"] == "bearer"


def test_login_redirects_to_role__token_encodes_role_and_sub() -> None:
    with patch("backend.routes.auth._fetch_user", return_value=_user(role="employee")):
        resp = client.post("/auth/login", json={"email": "user@example.com", "password": _PASSWORD})

    payload = decode_access_token(resp.json()["access_token"])
    assert payload is not None
    assert payload["role"] == "employee"
    assert payload["sub"] == "1"


def test_login_vendor_manager_token_includes_vendor_id() -> None:
    with patch("backend.routes.auth._fetch_user", return_value=_user(role="vendor_manager", vendor_id=7)):
        resp = client.post("/auth/login", json={"email": "user@example.com", "password": _PASSWORD})

    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "vendor_manager"
    assert body["vendor_id"] == 7
    payload = decode_access_token(body["access_token"])
    assert payload["vendor_id"] == 7


def test_login_wrong_password_returns_401_invalid_credentials() -> None:
    with patch("backend.routes.auth._fetch_user", return_value=_user()):
        resp = client.post("/auth/login", json={"email": "user@example.com", "password": "wrongpassword"})

    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_credentials"


def test_login_unknown_email_returns_401_invalid_credentials() -> None:
    with patch("backend.routes.auth._fetch_user", return_value=None):
        resp = client.post("/auth/login", json={"email": "nobody@example.com", "password": _PASSWORD})

    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_credentials"


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("role", ["employee", "vendor_manager"])
def test_register_new_user_returns_201_with_token(role: str) -> None:
    # _fetch_user returns what was actually written to the DB:
    # employee → is_active=False (pending approval); vendor_manager → is_active=True
    is_active = role != "employee"
    registered_user = _user(role=role, is_active=is_active)
    with (
        patch("backend.routes.auth.get_connection", return_value=_conn_ctx()),
        patch("backend.routes.auth._fetch_user", return_value=registered_user),
    ):
        resp = client.post(
            "/auth/register",
            json={"email": "new@example.com", "password": _PASSWORD, "display_name": "New User", "role": role},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert body["role"] == role
    assert body["user_id"] == 1
    assert body["is_active"] is is_active


def test_register_employee_starts_inactive() -> None:
    """Newly registered employees must be inactive until an admin enables them."""
    registered_user = _user(role="employee", is_active=False)
    with (
        patch("backend.routes.auth.get_connection", return_value=_conn_ctx(badge_code="EMP-0001")),
        patch("backend.routes.auth._fetch_user", return_value=registered_user),
    ):
        resp = client.post(
            "/auth/register",
            json={"email": "new.emp@example.com", "password": _PASSWORD, "display_name": "New Emp", "role": "employee"},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["is_active"] is False
    assert body["badge_code"] == "EMP-0001"


def test_register_vendor_manager_starts_active() -> None:
    """Vendor managers are active on registration (vendor approval is a separate step)."""
    registered_user = _user(role="vendor_manager", is_active=True)
    with (
        patch("backend.routes.auth.get_connection", return_value=_conn_ctx()),
        patch("backend.routes.auth._fetch_user", return_value=registered_user),
    ):
        resp = client.post(
            "/auth/register",
            json={"email": "new.vendor@example.com", "password": _PASSWORD, "display_name": "New Vendor", "role": "vendor_manager"},
        )

    assert resp.status_code == 201
    assert resp.json()["is_active"] is True


def test_register_existing_email_returns_409_email_taken() -> None:
    existing_row = MagicMock()
    with patch("backend.routes.auth.get_connection", return_value=_conn_ctx(existing_row=existing_row)):
        resp = client.post(
            "/auth/register",
            json={"email": "taken@example.com", "password": _PASSWORD, "display_name": "User", "role": "employee"},
        )

    assert resp.status_code == 409
    assert resp.json()["code"] == "email_taken"


def test_register_short_password_returns_422() -> None:
    resp = client.post(
        "/auth/register",
        json={"email": "new@example.com", "password": "short", "display_name": "User", "role": "employee"},
    )

    assert resp.status_code == 422
    assert resp.json()["code"] == "password_too_short"
