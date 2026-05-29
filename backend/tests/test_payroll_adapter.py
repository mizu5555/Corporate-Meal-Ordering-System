import pytest

from backend.schemas.billing import EmployeeTotal
from backend.services.payroll_adapter import PayrollAdapter


def test_payroll_adapter_formats_rows():
    adapter = PayrollAdapter()
    rows = adapter.export(2026, 5, [EmployeeTotal(employee_id=42, employee_name="Amy", amount_cents=1900)])
    assert rows == [{"employee_id": 42, "period": "2026-05", "amount_cents": 1900}]


def test_payroll_adapter_rejects_bad_period():
    adapter = PayrollAdapter()
    with pytest.raises(ValueError):
        adapter.export(2026, 13, [])
