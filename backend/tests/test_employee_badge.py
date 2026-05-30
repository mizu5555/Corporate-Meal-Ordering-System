"""Unit tests for GET /employee/me/badge."""
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.user_directory import get_user_repository
from backend.repositories.user_repository import UserRepository


@pytest.fixture()
def user_repo():
    repo = UserRepository()
    repo.add(id=1, display_name="王小明", role="employee", badge_code="EMP-0001")
    repo.add(id=2, display_name="No Badge", role="employee", badge_code=None)
    app.dependency_overrides[get_user_repository] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_user_repository, None)


@pytest.fixture()
def client():
    return TestClient(app)


def _emp(uid: int) -> dict[str, str]:
    return {"x-user-role": "employee", "x-user-id": str(uid)}


def test_returns_own_badge_and_name(client, user_repo):
    resp = client.get("/employee/me/badge", headers=_emp(1))
    assert resp.status_code == 200
    assert resp.json() == {"badge_code": "EMP-0001", "display_name": "王小明"}


def test_missing_badge_returns_badge_not_assigned(client, user_repo):
    resp = client.get("/employee/me/badge", headers=_emp(2))
    assert resp.status_code == 404
    assert "badge_not_assigned" in resp.text


def test_unknown_user_returns_badge_not_assigned(client, user_repo):
    resp = client.get("/employee/me/badge", headers=_emp(99))
    assert resp.status_code == 404
    assert "badge_not_assigned" in resp.text


def test_non_employee_role_forbidden(client, user_repo):
    resp = client.get("/employee/me/badge", headers={"x-user-role": "vendor_manager", "x-user-id": "1"})
    assert resp.status_code == 403
