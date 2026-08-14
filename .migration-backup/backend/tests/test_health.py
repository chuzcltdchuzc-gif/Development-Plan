from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_liveness_returns_ok() -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_503_when_database_unreachable() -> None:
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "reason": "database_unreachable"}
