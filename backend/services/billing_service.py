from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from backend.core.errors import CodedHTTPException
from backend.core.reporting import get_reporting_repository
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.schemas.billing import MonthlyStatement, VendorReceivable
from backend.services.notification_service import NotificationService
from backend.services.payroll_adapter import PayrollAdapter


def _validate_period(year: int, month: int) -> None:
    if not 1 <= month <= 12:
        raise CodedHTTPException(status_code=400, code="validation_error", detail="month must be 1-12")
    if not 2000 <= year <= 2100:
        raise CodedHTTPException(status_code=400, code="validation_error", detail="year out of range")


class BillingService:
    def __init__(
        self,
        reporting_repository=None,
        audit_log_repository: AuditLogRepository | None = None,
        notification_service: NotificationService | None = None,
        payroll_adapter: PayrollAdapter | None = None,
    ) -> None:
        self.reporting_repository = reporting_repository or get_reporting_repository()
        self.audit_log_repository = audit_log_repository or AuditLogRepository()
        self.notification_service = notification_service
        self.payroll_adapter = payroll_adapter or PayrollAdapter()

    def vendor_receivables(self, year: int, month: int) -> list[VendorReceivable]:
        _validate_period(year, month)
        return self.reporting_repository.vendor_monthly_receivables(year, month)

    def employee_payroll(self, year: int, month: int) -> list[dict]:
        _validate_period(year, month)
        totals = self.reporting_repository.employee_monthly_totals(year, month)
        return self.payroll_adapter.export(year, month, totals)

    def vendor_receivables_csv(self, year: int, month: int) -> str:
        rows = self.vendor_receivables(year, month)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["vendor_id", "vendor_name", "order_count", "quantity", "amount_cents"])
        for r in rows:
            writer.writerow([r.vendor_id, r.vendor_name, r.order_count, r.quantity, r.amount_cents])
        return buf.getvalue()

    def generate_statement(
        self, year: int, month: int, *, actor_user_id: int | None = None, actor_role: str | None = None
    ) -> MonthlyStatement:
        _validate_period(year, month)
        vendors = self.reporting_repository.vendor_monthly_receivables(year, month)
        totals = self.reporting_repository.employee_monthly_totals(year, month)
        statement = MonthlyStatement(
            year=year, month=month, generated_at=datetime.now(timezone.utc),
            vendors=vendors, employees=totals,
        )
        self.audit_log_repository.record(
            actor_user_id=actor_user_id, actor_role=actor_role,
            action="billing.statement", target_type="billing", target_id=None,
            metadata={"year": year, "month": month, "vendor_count": len(vendors), "employee_count": len(totals)},
        )
        if self.notification_service is not None:
            for v in vendors:
                if v.owner_user_id is not None:
                    self.notification_service.create_billing_statement_ready(
                        recipient_user_id=v.owner_user_id, year=year, month=month, amount_cents=v.amount_cents,
                    )
            for t in totals:
                self.notification_service.create_payroll_deduction_posted(
                    recipient_user_id=t.employee_id, year=year, month=month, amount_cents=t.amount_cents,
                )
        return statement
