from fastapi.testclient import TestClient

from backend.core.audit import get_audit_log_repository
from backend.main import app
from backend.repositories.audit_log_repository import AuditLogRepository

client = TestClient(app)


def _override(repo):
    app.dependency_overrides[get_audit_log_repository] = lambda: repo


def teardown_function():
    app.dependency_overrides.clear()


def test_requires_admin():
    _override(AuditLogRepository())
    r = client.get("/admin/audit-logs", headers={"x-user-role": "employee"})
    assert r.status_code == 403


def test_returns_entries_newest_first():
    repo = AuditLogRepository()
    repo.record(actor_user_id=1, actor_role="admin", action="a1", target_type="t", target_id=1)
    repo.record(actor_user_id=1, actor_role="admin", action="a2", target_type="t", target_id=2)
    _override(repo)
    r = client.get("/admin/audit-logs", headers={"x-user-role": "admin"})
    assert r.status_code == 200
    assert [e["action"] for e in r.json()] == ["a2", "a1"]


def test_filter_by_action_and_pagination():
    repo = AuditLogRepository()
    repo.record(actor_user_id=1, actor_role="admin", action="order.create", target_type="order", target_id=1)
    repo.record(actor_user_id=1, actor_role="admin", action="vendor.review", target_type="vendor_application", target_id=2)
    _override(repo)
    r = client.get("/admin/audit-logs?action=order.create", headers={"x-user-role": "admin"})
    assert [e["target_id"] for e in r.json()] == [1]
    r2 = client.get("/admin/audit-logs?limit=1", headers={"x-user-role": "admin"})
    assert len(r2.json()) == 1
