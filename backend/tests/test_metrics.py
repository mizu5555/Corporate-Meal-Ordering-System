from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_metrics_endpoint_returns_200() -> None:
    response = client.get("/metrics")
    assert response.status_code == 200


def test_metrics_endpoint_contains_http_counter() -> None:
    # Trigger one request so the counter exists
    client.get("/health")
    response = client.get("/metrics")
    assert "http_requests_total" in response.text
