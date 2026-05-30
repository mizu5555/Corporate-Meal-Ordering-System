from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.core.audit import get_audit_log_repository
from backend.core.rbac import get_current_user_id
from backend.main import app
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.routes.admin_vendors import get_vendor_repository
from backend.schemas.vendor import VendorApplicationDetail


client = TestClient(app)


class _FakeVendorRepository:
    """Minimal stand-in so the admin-review route never touches Postgres."""

    def __init__(self) -> None:
        self.reviewed: list[tuple] = []

    def get_application(self, application_id: int) -> VendorApplicationDetail | None:
        return VendorApplicationDetail(
            application_id=application_id,
            vendor_id=100,
            vendor_name="Alice Bento",
            status="pending",
            submitted_at=datetime.now(timezone.utc),
        )

    def mark_application_reviewed(
        self,
        application_id: int,
        *,
        decision: str,
        reviewer_user_id: int | None = None,
        reason: str | None = None,
    ) -> None:
        self.reviewed.append((application_id, decision, reviewer_user_id, reason))


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_non_admin_vendor_review_returns_403() -> None:
    response = client.post(
        "/admin/vendors/applications/1/review",
        json={"decision": "approved", "reason": "basic check"},
        headers={"x-user-role": "employee"},
    )

    assert response.status_code == 403


def test_vendor_review_records_audit_entry_with_actor() -> None:
    audit_repo = AuditLogRepository()
    vendor_repo = _FakeVendorRepository()
    app.dependency_overrides[get_vendor_repository] = lambda: vendor_repo
    app.dependency_overrides[get_audit_log_repository] = lambda: audit_repo
    app.dependency_overrides[get_current_user_id] = lambda: 42

    response = client.post(
        "/admin/vendors/applications/1/review",
        json={"decision": "approved", "reason": "basic check"},
        headers={"x-user-role": "admin", "x-user-id": "42"},
    )

    assert response.status_code == 202

    entries = audit_repo.list(action="vendor.review")
    assert len(entries) == 1
    entry = entries[0]
    assert entry.action == "vendor.review"
    assert entry.target_type == "vendor_application"
    assert entry.target_id == 1
    assert entry.actor_user_id == 42
    assert entry.actor_role == "admin"
    assert entry.metadata["decision"] == "approved"
