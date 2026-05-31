"""Tests for PATCH /auth/me/password."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend.core.security import create_access_token, hash_password
from backend.main import app

client = TestClient(app)

_PASSWORD = "oldpassword123"
_TOKEN = create_access_token({"sub": "42", "role": "employee"})
_HEADERS = {"Authorization": f"Bearer {_TOKEN}"}


def _pw_row(password: str = _PASSWORD) -> MagicMock:
    row = MagicMock()
    row.__getitem__ = lambda s, k: hash_password(password) if k == "password_hash" else None
    row.__bool__ = lambda s: True
    return row


def _conn_ctx(row=None, execute_side_effects=None) -> MagicMock:
    conn = MagicMock()
    if execute_side_effects:
        conn.execute.side_effect = execute_side_effects
    else:
        result = MagicMock()
        result.fetchone.return_value = row
        conn.execute.return_value = result
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


def test_change_password_success_returns_204() -> None:
    fetch_result = MagicMock()
    fetch_result.fetchone.return_value = {"password_hash": hash_password(_PASSWORD)}
    update_result = MagicMock()

    conn = MagicMock()
    conn.execute.side_effect = [fetch_result, update_result]
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)

    with patch("backend.routes.auth.get_connection", return_value=ctx):
        resp = client.patch(
            "/auth/me/password",
            headers=_HEADERS,
            json={"current_password": _PASSWORD, "new_password": "newpassword123"},
        )

    assert resp.status_code == 204


def test_change_password_wrong_current_returns_403() -> None:
    fetch_result = MagicMock()
    fetch_result.fetchone.return_value = {"password_hash": hash_password(_PASSWORD)}

    conn = MagicMock()
    conn.execute.return_value = fetch_result
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)

    with patch("backend.routes.auth.get_connection", return_value=ctx):
        resp = client.patch(
            "/auth/me/password",
            headers=_HEADERS,
            json={"current_password": "wrongpassword", "new_password": "newpassword123"},
        )

    assert resp.status_code == 403
    assert resp.json()["code"] == "wrong_current_password"


def test_change_password_too_short_returns_422() -> None:
    resp = client.patch(
        "/auth/me/password",
        headers=_HEADERS,
        json={"current_password": _PASSWORD, "new_password": "short"},
    )

    assert resp.status_code == 422
    assert resp.json()["code"] == "password_too_short"


def test_change_password_unauthenticated_returns_401() -> None:
    resp = client.patch(
        "/auth/me/password",
        json={"current_password": _PASSWORD, "new_password": "newpassword123"},
    )

    assert resp.status_code == 401
    assert resp.json()["code"] == "unauthenticated"
