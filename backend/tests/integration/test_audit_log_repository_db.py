import os
import pytest

from backend.repositories.postgres_audit_log_repository import PostgresAuditLogRepository

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="requires DATABASE_URL")


def test_record_and_list_roundtrip():
    repo = PostgresAuditLogRepository()
    repo.record(actor_user_id=1, actor_role="admin", action="vendor.review",
                target_type="vendor_application", target_id=999, metadata={"decision": "approved"})
    entries = repo.list(action="vendor.review", target_id=999)
    assert len(entries) >= 1
    e = entries[0]
    assert e.action == "vendor.review"
    assert e.actor_role == "admin"
    assert e.target_id == 999
    assert e.metadata == {"decision": "approved"}
