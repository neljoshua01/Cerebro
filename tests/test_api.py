from fastapi.testclient import TestClient

from cerebro.api.app import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_system_health() -> None:
    response = client.get("/api/system/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
