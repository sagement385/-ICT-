"""Health and readiness endpoint tests."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_does_not_require_database() -> None:
    """Health is available before optional infrastructure is configured."""

    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_invalid_incident_id_is_not_fabricated() -> None:
    """A DB-dependent lookup returns a configuration error without fake data."""

    response = TestClient(app).get("/api/v1/patients/TEST_MISSING_001")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_NOT_CONFIGURED"


def test_ready_endpoint_reports_database_not_ready() -> None:
    """Readiness does not claim success without a database connection."""

    response = TestClient(app).get("/api/v1/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_NOT_CONFIGURED"
