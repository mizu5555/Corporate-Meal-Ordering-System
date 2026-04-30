from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_non_committee_reviewer_returns_403() -> None:
    response = client.post(
        "/committee/reviews/1/decision",
        json={"decision": "approved", "reason": "looks good"},
        headers={"x-user-role": "employee"},
    )

    assert response.status_code == 403


def test_committee_reviewer_can_record_decision() -> None:
    response = client.post(
        "/committee/reviews/1/decision",
        json={"decision": "approved", "reason": "looks good"},
        headers={"x-user-role": "committee_reviewer"},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "review_recorded"
