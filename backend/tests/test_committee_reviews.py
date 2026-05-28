from fastapi.testclient import TestClient

from backend.core.audit import get_audit_log_repository
from backend.core.rbac import get_current_user_id
from backend.main import app
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.committee_review_repository import CommitteeReviewRecord, CommitteeReviewRepository
from backend.routes.committee_reviews import get_committee_review_repository


client = TestClient(app)


def _setup_repo() -> CommitteeReviewRepository:
    repo = CommitteeReviewRepository()
    repo.seed(
        CommitteeReviewRecord(
            id=1,
            target_type="vendor_application",
            target_id=10,
            title="Review Alice Bento",
            submitted_by_user_id=100,
        )
    )
    repo.seed(
        CommitteeReviewRecord(
            id=2,
            target_type="vendor_application",
            target_id=11,
            title="Already approved",
            status="approved",
        )
    )
    app.dependency_overrides[get_committee_review_repository] = lambda: repo
    return repo


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_non_committee_reviewer_returns_403() -> None:
    _setup_repo()
    response = client.post(
        "/committee/reviews/1/decision",
        json={"decision": "approved", "reason": "looks good"},
        headers={"x-user-role": "employee"},
    )

    assert response.status_code == 403


def test_committee_reviewer_can_list_pending_reviews() -> None:
    _setup_repo()

    response = client.get(
        "/committee/reviews/pending",
        headers={"x-user-role": "committee_reviewer"},
    )

    assert response.status_code == 200
    body = response.json()
    assert [review["id"] for review in body] == [1]
    assert body[0]["title"] == "Review Alice Bento"


def test_committee_reviewer_can_record_decision() -> None:
    repo = _setup_repo()

    response = client.post(
        "/committee/reviews/1/decision",
        json={"decision": "approved", "reason": "looks good"},
        headers={"x-user-role": "committee_reviewer"},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "approved"
    assert repo.get(1).status == "approved"


def test_committee_decision_records_audit_entry_with_actor() -> None:
    _setup_repo()
    audit_repo = AuditLogRepository()
    app.dependency_overrides[get_audit_log_repository] = lambda: audit_repo
    app.dependency_overrides[get_current_user_id] = lambda: 77

    response = client.post(
        "/committee/reviews/1/decision",
        json={"decision": "approved", "reason": "looks good"},
        headers={"x-user-role": "committee_reviewer", "x-user-id": "77"},
    )

    assert response.status_code == 202

    entries = audit_repo.list(action="committee.review")
    assert len(entries) == 1
    entry = entries[0]
    assert entry.action == "committee.review"
    assert entry.target_type == "committee_review"
    assert entry.target_id == 1
    assert entry.actor_user_id == 77
    assert entry.actor_role == "committee_reviewer"
    assert entry.metadata == {"decision": "approved", "reason": "looks good"}


def test_unknown_committee_review_returns_404() -> None:
    _setup_repo()

    response = client.post(
        "/committee/reviews/999/decision",
        json={"decision": "approved"},
        headers={"x-user-role": "committee_reviewer"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_decided_committee_review_returns_409() -> None:
    _setup_repo()

    response = client.post(
        "/committee/reviews/2/decision",
        json={"decision": "rejected"},
        headers={"x-user-role": "committee_reviewer"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "review_already_decided"
