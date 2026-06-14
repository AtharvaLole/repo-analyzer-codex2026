"""API smoke tests."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_agents_status_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/agents/status")

    assert response.status_code == 200
    assert response.json()["agents"]
