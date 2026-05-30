from __future__ import annotations

import csv
from io import StringIO

from backend.repositories.reporting_repository import ReportingRepository
from backend.schemas.billing import EmployeeTotal, MonthlyBillingSummary, VendorReceivable


class PayrollAdapter:
    def export(self, rows: list[EmployeeTotal], *, year: int, month: int) -> list[dict[str, object]]:
        period = f"{year:04d}-{month:02d}"
        return [
            {
                "employee_number": row.badge_code,
                "period": period,
                "amount": row.amount_cents,
            }
            for row in rows
        ]

    def export_csv(self, rows: list[EmployeeTotal], *, year: int, month: int) -> str:
        buffer = StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["employee_number", "period", "amount"])
        for row in self.export(rows, year=year, month=month):
            writer.writerow([row["employee_number"], row["period"], row["amount"]])
        return buffer.getvalue()


class BillingService:
    def __init__(
        self,
        reporting_repo: ReportingRepository,
        payroll_adapter: PayrollAdapter | None = None,
    ) -> None:
        self._reporting_repo = reporting_repo
        self._payroll_adapter = payroll_adapter or PayrollAdapter()

    def vendor_receivables(self, year: int, month: int) -> list[VendorReceivable]:
        return self._reporting_repo.vendor_monthly_receivables(year, month)

    def vendor_billing(self, vendor_id: int, year: int, month: int) -> MonthlyBillingSummary:
        row = next((r for r in self.vendor_receivables(year, month) if r.vendor_id == vendor_id), None)
        return MonthlyBillingSummary(
            year=year,
            month=month,
            amount_cents=row.amount_cents if row is not None else 0,
            order_count=row.order_count if row is not None else 0,
        )

    def vendor_receivables_csv(self, year: int, month: int) -> str:
        buffer = StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["vendor_id", "vendor_name", "period", "amount", "order_count"])
        period = f"{year:04d}-{month:02d}"
        for row in self.vendor_receivables(year, month):
            writer.writerow([row.vendor_id, row.vendor_name, period, row.amount_cents, row.order_count])
        return buffer.getvalue()

    def employee_payroll(self, year: int, month: int) -> list[EmployeeTotal]:
        return self._reporting_repo.employee_monthly_totals(year, month)

    def employee_payroll_export(self, year: int, month: int) -> list[dict[str, object]]:
        return self._payroll_adapter.export(self.employee_payroll(year, month), year=year, month=month)

    def employee_payroll_csv(self, year: int, month: int) -> str:
        return self._payroll_adapter.export_csv(self.employee_payroll(year, month), year=year, month=month)

    def employee_billing(self, employee_id: int, year: int, month: int) -> MonthlyBillingSummary:
        row = next((r for r in self.employee_payroll(year, month) if r.employee_id == employee_id), None)
        return MonthlyBillingSummary(
            year=year,
            month=month,
            amount_cents=row.amount_cents if row is not None else 0,
            order_count=row.order_count if row is not None else 0,
        )
