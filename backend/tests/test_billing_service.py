from datetime import date, datetime, timezone

import pytest

from backend.core.errors import CodedHTTPException
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.notification_repository import NotificationRepository
from backend.repositories.reporting_repository import ReportingRepository
from backend.services.billing_service import BillingService
from backend.services.notification_service import NotificationService


def _service():
    repo = ReportingRepository()
    repo.seed_order(
        order_id=1, vendor_id=1, vendor_name="Sunny Kitchen", facility_id=1,
        facility_name="Fab 12A", status="delivered",
        created_at=datetime(2026, 5, 2, tzinfo=timezone.utc), items=[(10, 2, 500)],
        employee_id=42, employee_name="Amy", meal_date=date(2026, 5, 3), owner_user_id=7,
    )
    audit = AuditLogRepository()
    notifs = NotificationService(NotificationRepository())
    svc = BillingService(reporting_repository=repo, audit_log_repository=audit, notification_service=notifs)
    return svc, audit, notifs


def test_vendor_receivables_and_payroll():
    svc, _, _ = _service()
    vendors = svc.vendor_receivables(2026, 5)
    assert vendors[0].amount_cents == 1000
    payroll = svc.employee_payroll(2026, 5)
    assert payroll == [{"employee_id": 42, "period": "2026-05", "amount_cents": 1000}]


def test_generate_statement_audits_and_notifies():
    svc, audit, notifs = _service()
    stmt = svc.generate_statement(2026, 5, actor_user_id=1, actor_role="admin")
    assert stmt.year == 2026 and stmt.month == 5
    assert stmt.vendors[0].vendor_id == 1
    assert any(e.action == "billing.statement" for e in audit.list(limit=10))
    assert notifs.list_unread(7)[0].type == "billing.statement_ready"
    assert notifs.list_unread(42)[0].type == "payroll.deduction_posted"


def test_invalid_month_rejected():
    svc, _, _ = _service()
    with pytest.raises(CodedHTTPException) as exc:
        svc.vendor_receivables(2026, 13)
    assert exc.value.status_code == 400


def test_csv_has_header_and_rows():
    svc, _, _ = _service()
    csv_text = svc.vendor_receivables_csv(2026, 5)
    lines = csv_text.strip().splitlines()
    assert lines[0] == "vendor_id,vendor_name,order_count,quantity,amount_cents"
    assert "1,Sunny Kitchen,1,2,1000" in csv_text
