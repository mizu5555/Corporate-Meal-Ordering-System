"""Employee identity guard tests."""
from fastapi.testclient import TestClient

from backend.core.security import create_access_token
from backend.core.user_directory import get_user_repository
from backend.main import app
from backend.repositories.user_repository import UserRepository

client = TestClient(app)


def _override_user_repo(repo: UserRepository) -> None:
    app.dependency_overrides[get_user_repository] = lambda: repo


def teardown_function() -> None:
    app.dependency_overrides.pop(get_user_repository, None)


def test_disabled_employee_with_existing_header_session_is_rejected() -> None:
    repo = UserRepository()
    repo.add(id=100, display_name="Inactive Employee", role="employee", is_active=False)
    _override_user_repo(repo)

    resp = client.get("/employee/vendors", headers={"x-user-role": "employee", "x-user-id": "100"})

    assert resp.status_code == 403
    assert resp.json()["code"] == "account_disabled"


def test_disabled_employee_with_existing_token_is_rejected() -> None:
    repo = UserRepository()
    repo.add(id=100, display_name="Inactive Employee", role="employee", is_active=False)
    _override_user_repo(repo)
    token = create_access_token({"sub": "100", "role": "employee"})

    resp = client.get("/employee/vendors", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 403
    assert resp.json()["code"] == "account_disabled"
