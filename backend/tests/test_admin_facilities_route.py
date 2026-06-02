"""Route tests for GET/POST /admin/facilities and GET/PUT /admin/vendors/{id}/facilities."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend.core.facilities import get_facility_repository
from backend.core.vendor_identity import get_vendor_profile_repository
from backend.main import app
from backend.repositories.facility_repository import FacilityRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord

client = TestClient(app)

_ADMIN_HEADERS = {"x-user-role": "admin"}
_COMMITTEE_HEADERS = {"x-user-role": "committee_reviewer"}
_EMPLOYEE_HEADERS = {"x-user-role": "employee"}


def _override_facility_repo(repo: FacilityRepository) -> None:
    app.dependency_overrides[get_facility_repository] = lambda: repo


def _override_vendor_repo(repo: VendorProfileRepository) -> None:
    app.dependency_overrides[get_vendor_profile_repository] = lambda: repo


def teardown_function() -> None:
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# RBAC guard
# ---------------------------------------------------------------------------


def test_list_facilities_employee_forbidden() -> None:
    _override_facility_repo(FacilityRepository())
    r = client.get("/admin/facilities", headers=_EMPLOYEE_HEADERS)
    assert r.status_code == 403


def test_create_facility_employee_forbidden() -> None:
    _override_facility_repo(FacilityRepository())
    r = client.post(
        "/admin/facilities",
        json={"code": "FAB1", "name": "Fab 1"},
        headers=_EMPLOYEE_HEADERS,
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# GET /admin/facilities
# ---------------------------------------------------------------------------


def test_list_facilities_empty_for_admin() -> None:
    _override_facility_repo(FacilityRepository())
    r = client.get("/admin/facilities", headers=_ADMIN_HEADERS)
    assert r.status_code == 200
    assert r.json() == []


def test_list_facilities_returns_seeded_data() -> None:
    repo = FacilityRepository()
    repo.create_facility("F12A", "Fab 12A")
    repo.create_facility("F12B", "Fab 12B")
    _override_facility_repo(repo)
    r = client.get("/admin/facilities", headers=_COMMITTEE_HEADERS)
    assert r.status_code == 200
    codes = [f["code"] for f in r.json()]
    assert codes == ["F12A", "F12B"]


# ---------------------------------------------------------------------------
# POST /admin/facilities
# ---------------------------------------------------------------------------


def test_create_facility_returns_201() -> None:
    _override_facility_repo(FacilityRepository())
    r = client.post(
        "/admin/facilities",
        json={"code": "FAB9", "name": "Fab 9"},
        headers=_ADMIN_HEADERS,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["code"] == "FAB9"
    assert body["name"] == "Fab 9"
    assert isinstance(body["id"], int)


def test_create_facility_idempotent_on_code() -> None:
    """Posting the same code twice returns the same facility (no 4xx)."""
    _override_facility_repo(FacilityRepository())
    r1 = client.post("/admin/facilities", json={"code": "DUP", "name": "First"}, headers=_ADMIN_HEADERS)
    r2 = client.post("/admin/facilities", json={"code": "DUP", "name": "Second"}, headers=_ADMIN_HEADERS)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


# ---------------------------------------------------------------------------
# GET /admin/vendors/{vendor_id}/facilities
# ---------------------------------------------------------------------------


def _setup_vendor_and_facility():
    """Return (facility_repo, vendor_repo) with vendor id=1 and facility id seeded."""
    f_repo = FacilityRepository()
    f_repo.create_facility("F01", "Fab 01")  # id=1
    v_repo = VendorProfileRepository()
    v_repo.seed(VendorRecord(id=1, name="Sunny Kitchen", status="approved"))
    return f_repo, v_repo


def test_get_vendor_facilities_empty() -> None:
    f_repo, v_repo = _setup_vendor_and_facility()
    _override_facility_repo(f_repo)
    _override_vendor_repo(v_repo)
    r = client.get("/admin/vendors/1/facilities", headers=_ADMIN_HEADERS)
    assert r.status_code == 200
    assert r.json() == []


def test_get_vendor_facilities_returns_assigned() -> None:
    f_repo, v_repo = _setup_vendor_and_facility()
    f_repo.set_vendor_facilities(1, [1])
    _override_facility_repo(f_repo)
    _override_vendor_repo(v_repo)
    r = client.get("/admin/vendors/1/facilities", headers=_ADMIN_HEADERS)
    assert r.status_code == 200
    assert r.json()[0]["code"] == "F01"


def test_get_vendor_facilities_missing_vendor_404() -> None:
    f_repo = FacilityRepository()
    v_repo = VendorProfileRepository()  # no vendors seeded
    _override_facility_repo(f_repo)
    _override_vendor_repo(v_repo)
    r = client.get("/admin/vendors/999/facilities", headers=_ADMIN_HEADERS)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# PUT /admin/vendors/{vendor_id}/facilities
# ---------------------------------------------------------------------------


def test_put_vendor_facilities_assigns_correctly() -> None:
    f_repo, v_repo = _setup_vendor_and_facility()
    _override_facility_repo(f_repo)
    _override_vendor_repo(v_repo)
    r = client.put(
        "/admin/vendors/1/facilities",
        json={"facility_ids": [1]},
        headers=_ADMIN_HEADERS,
    )
    assert r.status_code == 200
    assert r.json()[0]["code"] == "F01"


def test_put_vendor_facilities_nonexistent_facility_404() -> None:
    f_repo, v_repo = _setup_vendor_and_facility()
    _override_facility_repo(f_repo)
    _override_vendor_repo(v_repo)
    r = client.put(
        "/admin/vendors/1/facilities",
        json={"facility_ids": [999]},  # facility 999 does not exist
        headers=_ADMIN_HEADERS,
    )
    assert r.status_code == 404


def test_put_vendor_facilities_missing_vendor_404() -> None:
    f_repo = FacilityRepository()
    f_repo.create_facility("F01", "Fab 01")
    v_repo = VendorProfileRepository()  # no vendor seeded
    _override_facility_repo(f_repo)
    _override_vendor_repo(v_repo)
    r = client.put(
        "/admin/vendors/999/facilities",
        json={"facility_ids": [1]},
        headers=_ADMIN_HEADERS,
    )
    assert r.status_code == 404


def test_put_vendor_facilities_employee_forbidden() -> None:
    f_repo, v_repo = _setup_vendor_and_facility()
    _override_facility_repo(f_repo)
    _override_vendor_repo(v_repo)
    r = client.put(
        "/admin/vendors/1/facilities",
        json={"facility_ids": []},
        headers=_EMPLOYEE_HEADERS,
    )
    assert r.status_code == 403


def test_get_vendor_recommendation_limit_returns_default() -> None:
    _, v_repo = _setup_vendor_and_facility()
    _override_vendor_repo(v_repo)

    r = client.get("/admin/vendors/1/recommendation-limit", headers=_ADMIN_HEADERS)

    assert r.status_code == 200
    assert r.json() == {"vendor_id": 1, "daily_recommendation_limit": 3}


def test_put_vendor_recommendation_limit_updates_vendor() -> None:
    _, v_repo = _setup_vendor_and_facility()
    _override_vendor_repo(v_repo)

    r = client.put(
        "/admin/vendors/1/recommendation-limit",
        json={"daily_recommendation_limit": 2},
        headers=_ADMIN_HEADERS,
    )

    assert r.status_code == 200
    assert r.json() == {"vendor_id": 1, "daily_recommendation_limit": 2}
    assert v_repo.get(1).daily_recommendation_limit == 2


def test_put_vendor_recommendation_limit_rejects_out_of_range() -> None:
    _, v_repo = _setup_vendor_and_facility()
    _override_vendor_repo(v_repo)

    r = client.put(
        "/admin/vendors/1/recommendation-limit",
        json={"daily_recommendation_limit": 4},
        headers=_ADMIN_HEADERS,
    )

    assert r.status_code == 422


def test_put_vendor_recommendation_limit_employee_forbidden() -> None:
    _, v_repo = _setup_vendor_and_facility()
    _override_vendor_repo(v_repo)

    r = client.put(
        "/admin/vendors/1/recommendation-limit",
        json={"daily_recommendation_limit": 1},
        headers=_EMPLOYEE_HEADERS,
    )

    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Helper — mock the DB check in _assert_employee_exists
# ---------------------------------------------------------------------------


def _employee_conn(exists: bool = True, employee_id: int = 42) -> MagicMock:
    """Context-manager mock for get_connection() used in _assert_employee_exists."""
    result = MagicMock()
    result.fetchone.return_value = {"id": employee_id} if exists else None
    conn = MagicMock()
    conn.execute.return_value = result
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


# ---------------------------------------------------------------------------
# GET /admin/employees/{employee_id}/facilities
# ---------------------------------------------------------------------------


def test_get_employee_facilities_employee_role_forbidden() -> None:
    _override_facility_repo(FacilityRepository())
    r = client.get("/admin/employees/42/facilities", headers=_EMPLOYEE_HEADERS)
    assert r.status_code == 403


def test_get_employee_facilities_empty() -> None:
    _override_facility_repo(FacilityRepository())
    with patch("backend.routes.admin_facilities.get_connection", return_value=_employee_conn()):
        r = client.get("/admin/employees/42/facilities", headers=_ADMIN_HEADERS)
    assert r.status_code == 200
    assert r.json() == []


def test_get_employee_facilities_returns_assigned() -> None:
    repo = FacilityRepository()
    f = repo.create_facility("E01", "Employee Fab 1")
    repo.set_employee_facilities(42, [f.id])
    _override_facility_repo(repo)
    with patch("backend.routes.admin_facilities.get_connection", return_value=_employee_conn()):
        r = client.get("/admin/employees/42/facilities", headers=_ADMIN_HEADERS)
    assert r.status_code == 200
    assert r.json()[0]["code"] == "E01"


def test_get_employee_facilities_missing_employee_404() -> None:
    _override_facility_repo(FacilityRepository())
    with patch("backend.routes.admin_facilities.get_connection", return_value=_employee_conn(exists=False)):
        r = client.get("/admin/employees/999/facilities", headers=_ADMIN_HEADERS)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# PUT /admin/employees/{employee_id}/facilities
# ---------------------------------------------------------------------------


def test_put_employee_facilities_assigns_correctly() -> None:
    repo = FacilityRepository()
    f = repo.create_facility("E01", "Employee Fab 1")
    _override_facility_repo(repo)
    with patch("backend.routes.admin_facilities.get_connection", return_value=_employee_conn()):
        r = client.put(
            "/admin/employees/42/facilities",
            json={"facility_ids": [f.id]},
            headers=_ADMIN_HEADERS,
        )
    assert r.status_code == 200
    assert r.json()[0]["code"] == "E01"


def test_put_employee_facilities_empty_clears_assignment() -> None:
    repo = FacilityRepository()
    f = repo.create_facility("E01", "Employee Fab 1")
    repo.set_employee_facilities(42, [f.id])
    _override_facility_repo(repo)
    with patch("backend.routes.admin_facilities.get_connection", return_value=_employee_conn()):
        r = client.put(
            "/admin/employees/42/facilities",
            json={"facility_ids": []},
            headers=_ADMIN_HEADERS,
        )
    assert r.status_code == 200
    assert r.json() == []


def test_put_employee_facilities_nonexistent_facility_404() -> None:
    _override_facility_repo(FacilityRepository())
    with patch("backend.routes.admin_facilities.get_connection", return_value=_employee_conn()):
        r = client.put(
            "/admin/employees/42/facilities",
            json={"facility_ids": [9999]},
            headers=_ADMIN_HEADERS,
        )
    assert r.status_code == 404


def test_put_employee_facilities_missing_employee_404() -> None:
    _override_facility_repo(FacilityRepository())
    with patch("backend.routes.admin_facilities.get_connection", return_value=_employee_conn(exists=False)):
        r = client.put(
            "/admin/employees/42/facilities",
            json={"facility_ids": []},
            headers=_ADMIN_HEADERS,
        )
    assert r.status_code == 404


def test_put_employee_facilities_employee_role_forbidden() -> None:
    _override_facility_repo(FacilityRepository())
    r = client.put(
        "/admin/employees/42/facilities",
        json={"facility_ids": []},
        headers=_EMPLOYEE_HEADERS,
    )
    assert r.status_code == 403
