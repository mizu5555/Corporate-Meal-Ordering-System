"""Unit tests for the vendor application route.

Covers ``POST /vendor/applications`` and ``GET /vendor/applications/me`` by injecting a
fake repository through the route's ``get_vendor_repository`` dependency, so the tests
run without a database — mirroring the project's dependency-injection testing convention.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.core.facilities import get_facility_repository
from backend.main import app
from backend.routes.vendor_application import get_vendor_repository
from backend.schemas.vendor import VendorApplicationCreate, VendorApplicationDetail
from backend.schemas.vendor_self import Facility


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
            served_facilities=[
                Facility(id=fid, code=f"F{fid}", name=f"Facility {fid}")
                for fid in data.facility_ids
            ],
        )
        self._by_user[user_id] = detail
        self._next_id += 1
        return detail


class _FakeFacilityRepository:
    def __init__(self) -> None:
        self._facilities = [
            Facility(id=1, code="F12A", name="Fab 12A"),
            Facility(id=2, code="F14B", name="Fab 14B"),
        ]

    def list_facilities(self) -> list[Facility]:
        return list(self._facilities)

    def facility_exists(self, facility_id: int) -> bool:
        return any(facility.id == facility_id for facility in self._facilities)


@pytest.fixture()
def repo():
    fake = _FakeVendorRepository()
    app.dependency_overrides[get_vendor_repository] = lambda: fake
    app.dependency_overrides[get_facility_repository] = lambda: _FakeFacilityRepository()
    yield fake
    app.dependency_overrides.pop(get_vendor_repository, None)
    app.dependency_overrides.pop(get_facility_repository, None)


@pytest.fixture()
def client():
    return TestClient(app)


_VM_HEADERS = {"x-user-role": "vendor_manager", "x-user-id": "42"}


def _application_payload(**overrides):
    payload = {
        "vendor_name": "My Kitchen",
        "address": "1 Main St",
        "business_hours": "11:00-14:00",
        "contact_phone": "02-1234-5678",
        "contact_email": "k@example.com",
        "facility_ids": [1, 2],
    }
    payload.update(overrides)
    return payload


def test_submit_application_returns_created_detail(client, repo):
    resp = client.post(
        "/vendor/applications",
        headers=_VM_HEADERS,
        json=_application_payload(),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["vendor_name"] == "My Kitchen"
    assert body["status"] == "pending"
    assert body["address"] == "1 Main St"
    assert [facility["id"] for facility in body["served_facilities"]] == [1, 2]
    # the application is persisted under the calling user's id
    assert repo.get_my_application(42) is not None


@pytest.mark.usefixtures("repo")
def test_list_application_facilities_returns_available_facilities(client):
    resp = client.get("/vendor/applications/facilities", headers=_VM_HEADERS)

    assert resp.status_code == 200
    assert resp.json() == [
        {"id": 1, "code": "F12A", "name": "Fab 12A"},
        {"id": 2, "code": "F14B", "name": "Fab 14B"},
    ]


@pytest.mark.usefixtures("repo")
def test_submit_application_requires_required_fields(client):
    resp = client.post(
        "/vendor/applications",
        headers=_VM_HEADERS,
        json=_application_payload(address="   "),
    )

    assert resp.status_code == 400
    assert resp.json()["code"] == "validation_error"
    assert "address" in resp.json()["detail"]


@pytest.mark.usefixtures("repo")
def test_submit_application_requires_facility_selection(client):
    resp = client.post(
        "/vendor/applications",
        headers=_VM_HEADERS,
        json=_application_payload(facility_ids=[]),
    )

    assert resp.status_code == 400
    assert resp.json()["code"] == "validation_error"
    assert "facility_ids" in resp.json()["detail"]


@pytest.mark.usefixtures("repo")
def test_submit_application_rejects_unknown_facility(client):
    resp = client.post(
        "/vendor/applications",
        headers=_VM_HEADERS,
        json=_application_payload(facility_ids=[999]),
    )

    assert resp.status_code == 400
    assert resp.json()["code"] == "validation_error"
    assert "999" in resp.json()["detail"]


@pytest.mark.usefixtures("repo")
def test_submit_application_conflicts_when_one_already_exists(client):
    first = client.post(
        "/vendor/applications", headers=_VM_HEADERS, json=_application_payload(vendor_name="First")
    )
    assert first.status_code == 201
    second = client.post(
        "/vendor/applications", headers=_VM_HEADERS, json=_application_payload(vendor_name="Second")
    )
    assert second.status_code == 409
    assert "application_already_exists" in second.text


@pytest.mark.usefixtures("repo")
def test_get_my_application_returns_submitted_one(client):
    client.post(
        "/vendor/applications",
        headers=_VM_HEADERS,
        json=_application_payload(vendor_name="Mine", facility_ids=[1]),
    )
    resp = client.get("/vendor/applications/me", headers=_VM_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["vendor_name"] == "Mine"
    assert [facility["id"] for facility in resp.json()["served_facilities"]] == [1]


@pytest.mark.usefixtures("repo")
def test_get_my_application_returns_null_when_none(client):
    resp = client.get("/vendor/applications/me", headers=_VM_HEADERS)
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.usefixtures("repo")
def test_submit_application_requires_vendor_manager_role(client):
    resp = client.post(
        "/vendor/applications",
        headers={"x-user-role": "employee", "x-user-id": "42"},
        json=_application_payload(vendor_name="X"),
    )
    assert resp.status_code == 403


@pytest.mark.usefixtures("repo")
def test_submit_application_requires_user_id_header(client):
    resp = client.post(
        "/vendor/applications",
        headers={"x-user-role": "vendor_manager"},
        json=_application_payload(vendor_name="X"),
    )
    assert resp.status_code == 400
