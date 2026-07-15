"""Health and readiness endpoint tests."""

import pytest
from fastapi.testclient import TestClient

from app.core import database
from app.main import app


@pytest.fixture(autouse=True)
def isolate_database_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep endpoint tests independent from a developer's local PostgreSQL setting."""

    monkeypatch.setattr(database, "_engine", None)
    monkeypatch.setattr(database, "_session_factory", None)
    monkeypatch.setattr(database.get_settings(), "database_url", None)


def test_health_endpoint_does_not_require_database() -> None:
    """Health is available before optional infrastructure is configured."""

    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_local_frontend_origin_is_allowed() -> None:
    """The local Vite app can call the API across its development port."""

    response = TestClient(app).get(
        "/api/v1/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


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
