"""Unit tests for GET /admin/users, PATCH /{id}/disable, DELETE /{id}."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.core.security import create_access_token, hash_password
from backend.main import app

client = TestClient(app)

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)

_ADMIN_TOKEN = create_access_token({"sub": "1", "role": "admin"})
_ADMIN_HEADERS = {"Authorization": f"Bearer {_ADMIN_TOKEN}"}


def _make_user_row(
    id: int = 2,
    email: str = "employee@example.com",
    display_name: str = "Test User",
    role: str = "employee",
    is_active: bool = True,
) -> dict:
    return {
        "id": id,
        "email": email,
        "display_name": display_name,
        "role": role,
        "is_active": is_active,
        "created_at": _NOW,
    }


def _list_conn(rows: list[dict]) -> MagicMock:
    """Mock connection returning dicts from fetchall(); dict(dict) works fine."""
    result = MagicMock()
    result.fetchall.return_value = rows
    conn = MagicMock()
    conn.execute.return_value = result
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


def _action_conn(exists: bool = True) -> MagicMock:
    """Mock connection for disable/delete: first execute returns row or None, second is the mutation."""
    conn = MagicMock()
    check_result = MagicMock()
    check_result.fetchone.return_value = {"id": 2} if exists else None
    conn.execute.side_effect = [check_result, MagicMock()]
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


# ---------------------------------------------------------------------------
# RBAC guard
# ---------------------------------------------------------------------------

def test_list_users_non_admin_returns_403() -> None:
    resp = client.get("/admin/users", headers={"x-user-role": "employee"})
    assert resp.status_code == 403


def test_disable_user_non_admin_returns_403() -> None:
    resp = client.patch("/admin/users/2/disable", headers={"x-user-role": "employee"})
    assert resp.status_code == 403


def test_delete_user_non_admin_returns_403() -> None:
    resp = client.delete("/admin/users/2", headers={"x-user-role": "employee"})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /admin/users
# ---------------------------------------------------------------------------

def test_list_users_returns_200_with_user_list() -> None:
    rows = [_make_user_row()]
    with patch("backend.routes.admin_users.get_connection", return_value=_list_conn(rows)):
        resp = client.get("/admin/users", headers=_ADMIN_HEADERS)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["users"][0]["email"] == "employee@example.com"
    assert body["users"][0]["role"] == "employee"
    assert body["users"][0]["is_active"] is True


def test_list_users_empty_returns_zero_total() -> None:
    with patch("backend.routes.admin_users.get_connection", return_value=_list_conn([])):
        resp = client.get("/admin/users", headers=_ADMIN_HEADERS)

    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_list_users_search_param_is_forwarded() -> None:
    rows = [_make_user_row()]
    with patch("backend.routes.admin_users.get_connection", return_value=_list_conn(rows)) as mock_conn:
        resp = client.get("/admin/users?search=employee", headers=_ADMIN_HEADERS)

    assert resp.status_code == 200


def test_list_users_role_filter_param_is_forwarded() -> None:
    rows = [_make_user_row(role="vendor_manager")]
    with patch("backend.routes.admin_users.get_connection", return_value=_list_conn(rows)):
        resp = client.get("/admin/users?role=vendor_manager", headers=_ADMIN_HEADERS)

    assert resp.status_code == 200
    assert resp.json()["users"][0]["role"] == "vendor_manager"


# ---------------------------------------------------------------------------
# PATCH /admin/users/{id}/disable
# ---------------------------------------------------------------------------

def test_disable_user_returns_200() -> None:
    with patch("backend.routes.admin_users.get_connection", return_value=_action_conn(exists=True)):
        resp = client.patch("/admin/users/2/disable", headers=_ADMIN_HEADERS)

    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == 2
    assert body["is_active"] is False


def test_disable_nonexistent_user_returns_404() -> None:
    with patch("backend.routes.admin_users.get_connection", return_value=_action_conn(exists=False)):
        resp = client.patch("/admin/users/999/disable", headers=_ADMIN_HEADERS)

    assert resp.status_code == 404
    assert resp.json()["code"] == "user_not_found"


def test_disable_self_returns_403() -> None:
    resp = client.patch("/admin/users/1/disable", headers=_ADMIN_HEADERS)

    assert resp.status_code == 403
    assert resp.json()["code"] == "cannot_disable_self"


# ---------------------------------------------------------------------------
# DELETE /admin/users/{id}
# ---------------------------------------------------------------------------

def test_delete_user_returns_204() -> None:
    with patch("backend.routes.admin_users.get_connection", return_value=_action_conn(exists=True)):
        resp = client.delete("/admin/users/2", headers=_ADMIN_HEADERS)

    assert resp.status_code == 204


def test_delete_nonexistent_user_returns_404() -> None:
    with patch("backend.routes.admin_users.get_connection", return_value=_action_conn(exists=False)):
        resp = client.delete("/admin/users/999", headers=_ADMIN_HEADERS)

    assert resp.status_code == 404
    assert resp.json()["code"] == "user_not_found"


def test_delete_self_returns_403() -> None:
    resp = client.delete("/admin/users/1", headers=_ADMIN_HEADERS)

    assert resp.status_code == 403
    assert resp.json()["code"] == "cannot_delete_self"


# ---------------------------------------------------------------------------
# Login rejects disabled users
# ---------------------------------------------------------------------------

def test_login_disabled_user_returns_403_account_disabled() -> None:
    disabled_user = {
        "id": 5,
        "email": "disabled@example.com",
        "password_hash": hash_password("password123"),
        "is_active": False,
        "role": "employee",
        "vendor_id": None,
    }
    with patch("backend.routes.auth._fetch_user", return_value=disabled_user):
        resp = client.post("/auth/login", json={"email": "disabled@example.com", "password": "password123"})

    assert resp.status_code == 403
    assert resp.json()["code"] == "account_disabled"
