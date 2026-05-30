"""Unit tests for the in-memory UserRepository used by badge features."""
import pytest

from backend.repositories.user_repository import UserRepository, UserRecord


@pytest.fixture()
def repo():
    r = UserRepository()
    r.add(id=1, display_name="王小明", role="employee", badge_code="EMP-0001")
    r.add(id=2, display_name="John Smith", role="employee", badge_code="EMP-0002")
    r.add(id=3, display_name="Vendor Boss", role="vendor_manager", badge_code=None)
    return r


def test_get_by_badge_code_found(repo):
    user = repo.get_by_badge_code("EMP-0001")
    assert user is not None
    assert user.id == 1
    assert user.display_name == "王小明"


def test_get_by_badge_code_missing_returns_none(repo):
    assert repo.get_by_badge_code("EMP-9999") is None


def test_get_by_id_found(repo):
    user = repo.get_by_id(2)
    assert user is not None
    assert user.badge_code == "EMP-0002"


def test_get_by_id_missing_returns_none(repo):
    assert repo.get_by_id(99) is None


def test_next_badge_code_formats_and_increments():
    r = UserRepository()
    assert r.next_badge_code() == "EMP-0001"
    assert r.next_badge_code() == "EMP-0002"
