from datetime import datetime, timezone

from backend.schemas.billing import EmployeeTotal, MonthlyStatement, VendorReceivable


def test_billing_schema_shapes():
    stmt = MonthlyStatement(
        year=2026,
        month=5,
        generated_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        vendors=[
            VendorReceivable(
                vendor_id=1, vendor_name="Sunny Kitchen", owner_user_id=7,
                order_count=2, quantity=3, amount_cents=1500,
            )
        ],
        employees=[EmployeeTotal(employee_id=42, employee_name="Amy", amount_cents=900)],
    )
    assert stmt.vendors[0].owner_user_id == 7
    assert stmt.employees[0].amount_cents == 900
    assert stmt.month == 5
