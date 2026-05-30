"""Unit tests for the vendor application route.

Covers ``POST /vendor/applications`` and ``GET /vendor/applications/me`` by injecting a
fake repository through the route's ``get_vendor_repository`` dependency, so the tests
run without a database — mirroring the project's dependency-injection testing convention.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.routes.vendor_application import get_vendor_repository
from backend.schemas.vendor import VendorApplicationCreate, VendorApplicationDetail


class _FakeVendorRepository:
    """In-memory stand-in for VendorRepository covering only the application endpoints."""

    def __init__(self) -> None:
        self._by_user: dict[int, VendorApplicationDetail] = {}
        self._next_id = 1

    def get_my_application(self, user_id: int) -> VendorApplicationDetail | None:
        return self._by_user.get(user_id)

    def create_application(
        self, user_id: int, data: VendorApplicationCreate
    ) -> VendorApplicationDetail:
        detail = VendorApplicationDetail(
            application_id=self._next_id,
            vendor_id=100 + self._next_id,
            vendor_name=data.vendor_name,
            status="pending",
            submitted_at=datetime(2026, 5, 30, tzinfo=timezone.utc),
            address=data.address,
            business_hours=data.business_hours,
            contact_phone=data.contact_phone,
            contact_email=data.contact_email,
        )
        self._by_user[user_id] = detail
        self._next_id += 1
        return detail


@pytest.fixture()
def repo():
    fake = _FakeVendorRepository()
    app.dependency_overrides[get_vendor_repository] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_vendor_repository, None)


@pytest.fixture()
def client():
    return TestClient(app)


_VM_HEADERS = {"x-user-role": "vendor_manager", "x-user-id": "42"}


def test_submit_application_returns_created_detail(client, repo):
    resp = client.post(
        "/vendor/applications",
        headers=_VM_HEADERS,
        json={
            "vendor_name": "My Kitchen",
            "address": "1 Main St",
            "contact_email": "k@example.com",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["vendor_name"] == "My Kitchen"
    assert body["status"] == "pending"
    assert body["address"] == "1 Main St"
    # the application is persisted under the calling user's id
    assert repo.get_my_application(42) is not None


def test_submit_application_conflicts_when_one_already_exists(client, repo):
    first = client.post(
        "/vendor/applications", headers=_VM_HEADERS, json={"vendor_name": "First"}
    )
    assert first.status_code == 201
    second = client.post(
        "/vendor/applications", headers=_VM_HEADERS, json={"vendor_name": "Second"}
    )
    assert second.status_code == 409
    assert "application_already_exists" in second.text


def test_get_my_application_returns_submitted_one(client, repo):
    client.post("/vendor/applications", headers=_VM_HEADERS, json={"vendor_name": "Mine"})
    resp = client.get("/vendor/applications/me", headers=_VM_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["vendor_name"] == "Mine"


def test_get_my_application_returns_null_when_none(client, repo):
    resp = client.get("/vendor/applications/me", headers=_VM_HEADERS)
    assert resp.status_code == 200
    assert resp.json() is None


def test_submit_application_requires_vendor_manager_role(client, repo):
    resp = client.post(
        "/vendor/applications",
        headers={"x-user-role": "employee", "x-user-id": "42"},
        json={"vendor_name": "X"},
    )
    assert resp.status_code == 403


def test_submit_application_requires_user_id_header(client, repo):
    resp = client.post(
        "/vendor/applications",
        headers={"x-user-role": "vendor_manager"},
        json={"vendor_name": "X"},
    )
    assert resp.status_code == 400
