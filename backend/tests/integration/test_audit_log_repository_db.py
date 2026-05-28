import os
import pytest

from backend.repositories.postgres_audit_log_repository import PostgresAuditLogRepository

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="requires DATABASE_URL")


@pytest.fixture(scope="module", autouse=True)
def _migrated_db():
    """Apply migrations so audit_logs (incl. the actor_role column) exists.

    CI only psql-applies 001; the remaining migrations — including 010 which
    adds actor_role — are applied here via run_migrations(), matching the
    pattern in test_atomic_quota.py.
    """
    from backend.db.migrate import run_migrations

    run_migrations()


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


def test_record_with_nonexistent_actor_raises_fk_violation():
    """Regression for #56: the Postgres audit write enforces
    audit_logs.actor_user_id -> users(id). A synthetic actor id violates the FK.

    This is exactly the failure that surfaced when the full test suite ran
    against a real database: fake-domain unit tests create orders for synthetic
    employee ids, so their audit writes must go to the in-memory repo (the unit
    tests override get_audit_log_repository). Locking this behavior here makes
    the constraint — and the reason for that override — explicit.
    """
    import psycopg

    repo = PostgresAuditLogRepository()
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        repo.record(actor_user_id=99_999_999, actor_role="employee",
                    action="order.create", target_type="order", target_id=1)
