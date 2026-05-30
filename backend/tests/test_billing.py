from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from backend.core.vendor_identity import get_vendor_profile_repository
from backend.main import app
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository, OrderItemSnapshot
from backend.repositories.reporting_repository import ReportingRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord
from backend.routes.billing import get_reporting_repository
from backend.routes.employee_ordering import get_employee_selection_repository


def _seed_vendor_repo() -> VendorProfileRepository:
    repo = VendorProfileRepository()
    repo.seed(VendorRecord(id=1, name="Alice Bento", status="approved"))
    repo.seed(VendorRecord(id=2, name="Bob Noodles", status="approved"))
    return repo


def _client(selection_repo: EmployeeSelectionRepository) -> TestClient:
    vendor_repo = _seed_vendor_repo()
    app.dependency_overrides[get_vendor_profile_repository] = lambda: vendor_repo
    app.dependency_overrides[get_employee_selection_repository] = lambda: selection_repo
    app.dependency_overrides[get_reporting_repository] = lambda: ReportingRepository(selection_repo, vendor_repo)
    return TestClient(app)


def _employee_headers(employee_id: int = 100) -> dict[str, str]:
    return {"x-user-role": "employee", "x-user-id": str(employee_id)}


def _vendor_headers(vendor_id: int = 1) -> dict[str, str]:
    return {"x-user-role": "vendor_manager", "x-vendor-id": str(vendor_id)}


def _admin_headers(role: str = "committee_reviewer") -> dict[str, str]:
    return {"x-user-role": role}


def _order(
    repo: EmployeeSelectionRepository,
    *,
    employee_id: int,
    vendor_id: int,
    meal_date: date,
    amount_cents: int,
    status: str = "delivered",
) -> None:
    order = repo.create_order(
        employee_id=employee_id,
        vendor_id=vendor_id,
        meal_date=meal_date,
        items=[
            OrderItemSnapshot(
                item_id=1,
                item_name="Bento",
                quantity=1,
                unit_price_cents=amount_cents,
            )
        ],
    )
    if status != "pending":
        repo.update_order_status(vendor_id=vendor_id, order_id=order.id, new_status=status)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_employee_billing_returns_only_callers_delivered_total() -> None:
    repo = EmployeeSelectionRepository()
    _order(repo, employee_id=100, vendor_id=1, meal_date=date(2026, 5, 3), amount_cents=12000)
    _order(repo, employee_id=100, vendor_id=1, meal_date=date(2026, 5, 4), amount_cents=9000, status="pending")
    _order(repo, employee_id=200, vendor_id=1, meal_date=date(2026, 5, 5), amount_cents=45000)
    _order(repo, employee_id=100, vendor_id=1, meal_date=date(2026, 4, 30), amount_cents=33000)

    resp = _client(repo).get("/employee/me/billing?year=2026&month=5", headers=_employee_headers(100))

    assert resp.status_code == 200
    assert resp.json() == {"year": 2026, "month": 5, "amount_cents": 12000, "order_count": 1}


def test_employee_billing_requires_employee_role() -> None:
    resp = _client(EmployeeSelectionRepository()).get(
        "/employee/me/billing?year=2026&month=5",
        headers={"x-user-role": "vendor_manager", "x-vendor-id": "1"},
    )

    assert resp.status_code == 403


def test_vendor_billing_returns_only_own_delivered_receivable() -> None:
    repo = EmployeeSelectionRepository()
    _order(repo, employee_id=100, vendor_id=1, meal_date=date(2026, 5, 3), amount_cents=12000)
    _order(repo, employee_id=101, vendor_id=1, meal_date=date(2026, 5, 4), amount_cents=8000)
    _order(repo, employee_id=102, vendor_id=2, meal_date=date(2026, 5, 4), amount_cents=99000)
    _order(repo, employee_id=100, vendor_id=1, meal_date=date(2026, 5, 5), amount_cents=5000, status="cancelled")

    resp = _client(repo).get("/vendor/me/billing?year=2026&month=5", headers=_vendor_headers(1))

    assert resp.status_code == 200
    assert resp.json() == {"year": 2026, "month": 5, "amount_cents": 20000, "order_count": 2}


def test_vendor_billing_empty_month_returns_zero_summary() -> None:
    resp = _client(EmployeeSelectionRepository()).get(
        "/vendor/me/billing?year=2026&month=5",
        headers=_vendor_headers(1),
    )

    assert resp.status_code == 200
    assert resp.json() == {"year": 2026, "month": 5, "amount_cents": 0, "order_count": 0}


def test_payroll_csv_is_keyed_by_employee_badge_code() -> None:
    repo = EmployeeSelectionRepository()
    _order(repo, employee_id=100, vendor_id=1, meal_date=date(2026, 5, 3), amount_cents=12000)
    _order(repo, employee_id=101, vendor_id=2, meal_date=date(2026, 5, 4), amount_cents=23000)

    resp = _client(repo).get("/admin/billing/payroll.csv?year=2026&month=5", headers=_admin_headers())

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert 'filename="payroll-deductions-2026-05.csv"' in resp.headers["content-disposition"]
    assert resp.text.splitlines() == [
        "employee_number,period,amount",
        "EMP-0100,2026-05,12000",
        "EMP-0101,2026-05,23000",
    ]


def test_reconciliation_employee_deductions_equal_vendor_receivables() -> None:
    repo = EmployeeSelectionRepository()
    _order(repo, employee_id=100, vendor_id=1, meal_date=date(2026, 5, 3), amount_cents=12000)
    _order(repo, employee_id=100, vendor_id=2, meal_date=date(2026, 5, 4), amount_cents=8000)
    _order(repo, employee_id=101, vendor_id=1, meal_date=date(2026, 5, 4), amount_cents=23000)
    _order(repo, employee_id=101, vendor_id=2, meal_date=date(2026, 5, 5), amount_cents=5000, status="pending")

    client = _client(repo)
    payroll = client.get("/admin/billing/payroll?year=2026&month=5", headers=_admin_headers()).json()
    receivables = client.get("/admin/billing/vendors?year=2026&month=5", headers=_admin_headers()).json()

    assert sum(row["amount_cents"] for row in payroll) == 43000
    assert sum(row["amount_cents"] for row in receivables) == 43000


def test_admin_billing_requires_admin_or_committee_role() -> None:
    resp = _client(EmployeeSelectionRepository()).get(
        "/admin/billing/payroll?year=2026&month=5",
        headers=_employee_headers(100),
    )

    assert resp.status_code == 403
