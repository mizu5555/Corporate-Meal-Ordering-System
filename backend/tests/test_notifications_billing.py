from backend.repositories.notification_repository import NotificationRepository
from backend.services.notification_service import NotificationService


def test_billing_statement_ready_notification():
    svc = NotificationService(NotificationRepository())
    n = svc.create_billing_statement_ready(recipient_user_id=7, year=2026, month=5, amount_cents=1500)
    assert n.type == "billing.statement_ready"
    assert n.payload["amount_cents"] == 1500
    assert n.payload["year"] == 2026 and n.payload["month"] == 5
    assert svc.list_unread(7)[0].type == "billing.statement_ready"


def test_payroll_deduction_posted_notification():
    svc = NotificationService(NotificationRepository())
    n = svc.create_payroll_deduction_posted(recipient_user_id=42, year=2026, month=5, amount_cents=1900)
    assert n.type == "payroll.deduction_posted"
    assert n.payload["amount_cents"] == 1900
    assert svc.list_unread(42)[0].type == "payroll.deduction_posted"
