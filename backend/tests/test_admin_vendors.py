from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_non_admin_vendor_review_returns_403() -> None:
    response = client.post(
        "/admin/vendors/1/review",
        json={"decision": "approved", "reason": "basic check"},
        headers={"x-user-role": "employee"},
    )

    assert response.status_code == 403
