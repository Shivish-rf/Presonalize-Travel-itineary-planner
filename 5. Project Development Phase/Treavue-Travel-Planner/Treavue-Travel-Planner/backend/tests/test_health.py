from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_docs_page_is_available() -> None:
    response = client.get("/docs")
    assert response.status_code == 200
