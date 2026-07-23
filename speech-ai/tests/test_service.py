"""Speech boundary health and fail-closed provider tests."""

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.config import get_settings
from app.main import app


def test_health_stays_available_without_model_providers() -> None:
    """An optional model must not prevent the service health endpoint from starting."""

    get_settings.cache_clear()
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "speech-ai"}


def test_status_reports_missing_providers(monkeypatch: MonkeyPatch) -> None:
    """Provider absence is explicit and never represented as a working model."""

    monkeypatch.setenv("SPEECH_STT_PROVIDER", "")
    monkeypatch.setenv("SPEECH_ENTITY_EXTRACTOR", "")
    get_settings.cache_clear()
    with TestClient(app) as client:
        response = client.get("/status")
    get_settings.cache_clear()

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "not_configured"
    assert set(payload["missing_settings"]) == {
        "SPEECH_STT_PROVIDER",
        "SPEECH_ENTITY_EXTRACTOR",
    }
    assert payload["medical_decision_support_only"] is True
