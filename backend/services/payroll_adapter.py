"""Stub adapter to the corporate payroll-deduction system.

Contract: given a period and per-employee monthly totals, produce payroll rows
(`employee_id`, `period` as YYYY-MM, `amount_cents`). A real adapter (HTTP/file
hand-off) can replace `export` without touching BillingService. Errors propagate
— deductions must never be silently dropped.
"""
from __future__ import annotations

from backend.schemas.billing import EmployeeTotal


class PayrollAdapter:
    def export(self, year: int, month: int, totals: list[EmployeeTotal]) -> list[dict]:
        if not 1 <= month <= 12:
            raise ValueError(f"invalid month: {month}")
        period = f"{year:04d}-{month:02d}"
        return [
            {"employee_id": t.employee_id, "period": period, "amount_cents": t.amount_cents}
            for t in totals
        ]
