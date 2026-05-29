from datetime import date, datetime, timezone

from backend.repositories.reporting_repository import ReportingRepository


def _seed(repo: ReportingRepository) -> None:
    repo.seed_order(
        order_id=1, vendor_id=1, vendor_name="Sunny Kitchen", facility_id=1,
        facility_name="Fab 12A", status="delivered",
        created_at=datetime(2026, 5, 2, tzinfo=timezone.utc),
        items=[(10, 2, 500)], employee_id=42, employee_name="Amy",
        meal_date=date(2026, 5, 3), owner_user_id=7,
    )
    repo.seed_order(
        order_id=2, vendor_id=2, vendor_name="Noodle Bar", facility_id=1,
        facility_name="Fab 12A", status="delivered",
        created_at=datetime(2026, 5, 4, tzinfo=timezone.utc),
        items=[(20, 1, 900)], employee_id=42, employee_name="Amy",
        meal_date=date(2026, 5, 5), owner_user_id=8,
    )
    repo.seed_order(
        order_id=3, vendor_id=1, vendor_name="Sunny Kitchen", facility_id=1,
        facility_name="Fab 12A", status="pending",
        created_at=datetime(2026, 5, 6, tzinfo=timezone.utc),
        items=[(10, 5, 500)], employee_id=99, employee_name="Bob",
        meal_date=date(2026, 5, 6), owner_user_id=7,
    )
    repo.seed_order(
        order_id=4, vendor_id=1, vendor_name="Sunny Kitchen", facility_id=1,
        facility_name="Fab 12A", status="delivered",
        created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        items=[(10, 1, 500)], employee_id=42, employee_name="Amy",
        meal_date=date(2026, 6, 1), owner_user_id=7,
    )


def test_vendor_monthly_receivables_delivered_only():
    repo = ReportingRepository()
    _seed(repo)
    rows = repo.vendor_monthly_receivables(2026, 5)
    by_vendor = {r.vendor_id: r for r in rows}
    assert set(by_vendor) == {1, 2}
    assert by_vendor[1].amount_cents == 1000
    assert by_vendor[1].owner_user_id == 7
    assert by_vendor[2].amount_cents == 900


def test_employee_monthly_totals_delivered_only():
    repo = ReportingRepository()
    _seed(repo)
    rows = repo.employee_monthly_totals(2026, 5)
    by_emp = {r.employee_id: r for r in rows}
    assert set(by_emp) == {42}
    assert by_emp[42].amount_cents == 1900
    assert by_emp[42].employee_name == "Amy"
