from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from backend.core.reporting import get_reporting_repository
from backend.core.vendor_identity import get_vendor_profile_repository
from backend.main import app
from backend.repositories.reporting_repository import ReportingRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord
from backend.schemas.billing import EmployeeTotal, MonthlyStatement, VendorReceivable


def _seed_vendor_repo() -> VendorProfileRepository:
    repo = VendorProfileRepository()
    repo.seed(VendorRecord(id=1, name="Alice Bento", status="approved"))
    repo.seed(VendorRecord(id=2, name="Bob Noodles", status="approved"))
    return repo


def _client(repo: ReportingRepository) -> TestClient:
    app.dependency_overrides[get_reporting_repository] = lambda: repo
    app.dependency_overrides[get_vendor_profile_repository] = _seed_vendor_repo
    return TestClient(app)


def _employee_headers(employee_id: int = 100) -> dict[str, str]:
    return {"x-user-role": "employee", "x-user-id": str(employee_id)}


def _vendor_headers(vendor_id: int = 1) -> dict[str, str]:
    return {"x-user-role": "vendor_manager", "x-vendor-id": str(vendor_id)}


def _admin_headers(role: str = "committee_reviewer") -> dict[str, str]:
    return {"x-user-role": role}


def _order(
    repo: ReportingRepository,
    *,
    order_id: int,
    employee_id: int,
    vendor_id: int,
    vendor_name: str,
    meal_date: date,
    amount_cents: int,
    status: str = "delivered",
) -> None:
    repo.seed_order(
        order_id=order_id,
        vendor_id=vendor_id,
        vendor_name=vendor_name,
        facility_id=1,
        facility_name="HQ",
        status=status,
        created_at=datetime(meal_date.year, meal_date.month, meal_date.day, tzinfo=timezone.utc),
        items=[(1, 1, amount_cents)],
        employee_id=employee_id,
        employee_name=f"Employee {employee_id}",
        meal_date=meal_date,
    )


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_employee_billing_returns_only_callers_delivered_total() -> None:
    repo = ReportingRepository()
    _order(repo, order_id=1, employee_id=100, vendor_id=1, vendor_name="Alice Bento", meal_date=date(2026, 5, 3), amount_cents=12000)
    _order(repo, order_id=2, employee_id=100, vendor_id=1, vendor_name="Alice Bento", meal_date=date(2026, 5, 4), amount_cents=9000, status="pending")
    _order(repo, order_id=3, employee_id=200, vendor_id=1, vendor_name="Alice Bento", meal_date=date(2026, 5, 5), amount_cents=45000)
    _order(repo, order_id=4, employee_id=100, vendor_id=1, vendor_name="Alice Bento", meal_date=date(2026, 4, 30), amount_cents=33000)

    resp = _client(repo).get("/employee/me/billing?year=2026&month=5", headers=_employee_headers(100))

    assert resp.status_code == 200
    assert resp.json() == {"year": 2026, "month": 5, "amount_cents": 12000, "order_count": 1}


def test_employee_billing_requires_employee_role() -> None:
    resp = _client(ReportingRepository()).get(
        "/employee/me/billing?year=2026&month=5",
        headers={"x-user-role": "vendor_manager", "x-vendor-id": "1"},
    )

    assert resp.status_code == 403


def test_vendor_billing_returns_only_own_delivered_receivable() -> None:
    repo = ReportingRepository()
    _order(repo, order_id=1, employee_id=100, vendor_id=1, vendor_name="Alice Bento", meal_date=date(2026, 5, 3), amount_cents=12000)
    _order(repo, order_id=2, employee_id=101, vendor_id=1, vendor_name="Alice Bento", meal_date=date(2026, 5, 4), amount_cents=8000)
    _order(repo, order_id=3, employee_id=102, vendor_id=2, vendor_name="Bob Noodles", meal_date=date(2026, 5, 4), amount_cents=99000)
    _order(repo, order_id=4, employee_id=100, vendor_id=1, vendor_name="Alice Bento", meal_date=date(2026, 5, 5), amount_cents=5000, status="cancelled")

    resp = _client(repo).get("/vendor/me/billing?year=2026&month=5", headers=_vendor_headers(1))

    assert resp.status_code == 200
    assert resp.json() == {"year": 2026, "month": 5, "amount_cents": 20000, "order_count": 2}


def test_vendor_billing_empty_month_returns_zero_summary() -> None:
    resp = _client(ReportingRepository()).get(
        "/vendor/me/billing?year=2026&month=5",
        headers=_vendor_headers(1),
    )

    assert resp.status_code == 200
    assert resp.json() == {"year": 2026, "month": 5, "amount_cents": 0, "order_count": 0}


def test_payroll_csv_is_keyed_by_employee_badge_code() -> None:
    repo = ReportingRepository()
    _order(repo, order_id=1, employee_id=100, vendor_id=1, vendor_name="Alice Bento", meal_date=date(2026, 5, 3), amount_cents=12000)
    _order(repo, order_id=2, employee_id=101, vendor_id=2, vendor_name="Bob Noodles", meal_date=date(2026, 5, 4), amount_cents=23000)

    resp = _client(repo).get("/admin/billing/payroll.csv?year=2026&month=5", headers=_admin_headers())

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert 'filename="payroll-deductions-2026-05.csv"' in resp.headers["content-disposition"]
    assert resp.text.splitlines() == [
        "employee_number,period,amount",
        "EMP-0101,2026-05,23000",
        "EMP-0100,2026-05,12000",
    ]


def test_reconciliation_employee_deductions_equal_vendor_receivables() -> None:
    repo = ReportingRepository()
    _order(repo, order_id=1, employee_id=100, vendor_id=1, vendor_name="Alice Bento", meal_date=date(2026, 5, 3), amount_cents=12000)
    _order(repo, order_id=2, employee_id=100, vendor_id=2, vendor_name="Bob Noodles", meal_date=date(2026, 5, 4), amount_cents=8000)
    _order(repo, order_id=3, employee_id=101, vendor_id=1, vendor_name="Alice Bento", meal_date=date(2026, 5, 4), amount_cents=23000)
    _order(repo, order_id=4, employee_id=101, vendor_id=2, vendor_name="Bob Noodles", meal_date=date(2026, 5, 5), amount_cents=5000, status="pending")

    client = _client(repo)
    payroll = client.get("/admin/billing/payroll?year=2026&month=5", headers=_admin_headers()).json()
    receivables = client.get("/admin/billing/vendors?year=2026&month=5", headers=_admin_headers()).json()

    assert sum(row["amount_cents"] for row in payroll) == 43000
    assert sum(row["amount_cents"] for row in receivables) == 43000


def test_admin_billing_requires_admin_or_committee_role() -> None:
    resp = _client(ReportingRepository()).get(
        "/admin/billing/payroll?year=2026&month=5",
        headers=_employee_headers(100),
    )

    assert resp.status_code == 403


def test_billing_schema_shapes() -> None:
    stmt = MonthlyStatement(
        year=2026,
        month=5,
        generated_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        vendors=[
            VendorReceivable(
                vendor_id=1,
                vendor_name="Sunny Kitchen",
                owner_user_id=7,
                order_count=2,
                quantity=3,
                amount_cents=1500,
            )
        ],
        employees=[EmployeeTotal(employee_id=42, employee_name="Amy", amount_cents=900)],
    )
    assert stmt.vendors[0].owner_user_id == 7
    assert stmt.employees[0].amount_cents == 900
    assert stmt.month == 5
