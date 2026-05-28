from backend.repositories.audit_log_repository import AuditLogRepository


def _record(repo, **over):
    base = dict(actor_user_id=1, actor_role="admin", action="vendor.review",
               target_type="vendor_application", target_id=7, metadata={"decision": "approved"})
    base.update(over)
    repo.record(**base)


def test_record_then_list_returns_entry():
    repo = AuditLogRepository()
    _record(repo)
    entries = repo.list()
    assert len(entries) == 1
    e = entries[0]
    assert e.actor_user_id == 1
    assert e.actor_role == "admin"
    assert e.action == "vendor.review"
    assert e.target_type == "vendor_application"
    assert e.target_id == 7
    assert e.metadata == {"decision": "approved"}
    assert e.id == 1


def test_list_orders_newest_first():
    repo = AuditLogRepository()
    _record(repo, action="a1")
    _record(repo, action="a2")
    actions = [e.action for e in repo.list()]
    assert actions == ["a2", "a1"]


def test_list_filters_and_pagination():
    repo = AuditLogRepository()
    _record(repo, action="order.create", target_type="order", target_id=1, actor_user_id=5)
    _record(repo, action="vendor.review", target_type="vendor_application", target_id=2, actor_user_id=1)
    _record(repo, action="order.create", target_type="order", target_id=3, actor_user_id=5)
    assert [e.target_id for e in repo.list(action="order.create")] == [3, 1]
    assert [e.target_id for e in repo.list(actor_user_id=1)] == [2]
    assert [e.target_id for e in repo.list(target_type="order", target_id=1)] == [1]
    assert len(repo.list(limit=1)) == 1
    assert repo.list(limit=1, offset=1)[0].action == "vendor.review"


def test_record_defaults_metadata_to_empty_dict():
    repo = AuditLogRepository()
    repo.record(actor_user_id=1, actor_role="admin", action="user.delete",
                target_type="user", target_id=9)
    assert repo.list()[0].metadata == {}
