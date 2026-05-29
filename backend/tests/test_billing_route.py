from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from backend.core.reporting import get_reporting_repository
from backend.main import app
from backend.repositories.reporting_repository import ReportingRepository

client = TestClient(app)


def _seeded_repo():
    repo = ReportingRepository()
    repo.seed_order(
        order_id=1, vendor_id=1, vendor_name="Sunny Kitchen", facility_id=1,
        facility_name="Fab 12A", status="delivered",
        created_at=datetime(2026, 5, 2, tzinfo=timezone.utc), items=[(10, 2, 500)],
        employee_id=42, employee_name="Amy", meal_date=date(2026, 5, 3), owner_user_id=7,
    )
    return repo


def _override(repo):
    app.dependency_overrides[get_reporting_repository] = lambda: repo


def teardown_function():
    app.dependency_overrides.clear()


def test_requires_admin_or_committee():
    _override(ReportingRepository())
    r = client.get("/admin/billing/vendors?year=2026&month=5", headers={"x-user-role": "employee"})
    assert r.status_code == 403


def test_vendor_receivables_json():
    _override(_seeded_repo())
    r = client.get("/admin/billing/vendors?year=2026&month=5", headers={"x-user-role": "admin"})
    assert r.status_code == 200
    assert r.json()[0]["amount_cents"] == 1000


def test_vendor_receivables_csv():
    _override(_seeded_repo())
    r = client.get("/admin/billing/vendors.csv?year=2026&month=5", headers={"x-user-role": "committee_reviewer"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "Sunny Kitchen" in r.text


def test_generate_statement_endpoint():
    _override(_seeded_repo())
    r = client.post("/admin/billing/statements?year=2026&month=5", headers={"x-user-role": "admin"})
    assert r.status_code == 200
    assert r.json()["vendors"][0]["vendor_id"] == 1


def test_invalid_month():
    _override(ReportingRepository())
    r = client.get("/admin/billing/vendors?year=2026&month=13", headers={"x-user-role": "admin"})
    assert r.status_code == 400
