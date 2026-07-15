"""Tests for safe Gemini chat assistance using only test doubles."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import patients as patients_api
from app.core.errors import ApplicationError
from app.integrations.gemini.client import GeminiClient
from app.integrations.gemini.schemas import GeminiExtraction
from app.main import app
from app.modules.patient.assist_service import PatientAssistService
from app.modules.patient.schemas import (
    PatientAssistResponse,
    PatientEventSource,
    PatientSymptomInput,
)

ROOT = Path(__file__).resolve().parents[2]


class FakeGeminiClient:
    """Deterministic client used instead of an external model in unit tests."""

    async def extract_patient_facts(self, text: str) -> GeminiExtraction:
        """Return explicit test facts and an intentionally unsafe urgency value."""

        assert text
        return GeminiExtraction(
            symptom_labels=["TEST_SYMPTOM"],
            consciousness_status="의식 있음",
            breathing_status="확인 불가",
            bleeding_status="확인 불가",
            urgency_level="Level 4",
            location_text="TEST_LOCATION",
        )


def test_gemini_fixture_is_explicitly_test_only() -> None:
    """The fixture uses placeholders rather than operational patient data."""

    fixture = json.loads(
        (ROOT / "backend/tests/fixtures/gemini-assist-test.json").read_text(encoding="utf-8")
    )
    assert "TEST_" in fixture["text"]


@pytest.mark.asyncio
async def test_assist_requires_human_review_and_discards_inferred_urgency() -> None:
    """The service does not accept an urgency level absent from user text."""

    result = await PatientAssistService(client=FakeGeminiClient()).assist(
        "TEST_PERSON이 TEST_LOCATION에서 가슴이 아프다고 말했습니다."
    )
    assert result.needs_human_review is True
    assert result.urgency_level is None
    assert result.symptoms[0].code == "GEMINI_SYMPTOM_1"
    assert result.symptoms[0].confidence is None
    assert len(result.warnings) >= 2


def test_assist_endpoint_uses_contract_without_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """The chat extraction endpoint can be tested without persistence."""

    class FakeAssistService:
        async def assist(self, text: str) -> PatientAssistResponse:
            assert text == "TEST input"
            return PatientAssistResponse(
                symptoms=[PatientSymptomInput(code="TEST_SYMPTOM", label="TEST symptom")],
                needs_human_review=True,
                warnings=["TEST human review"],
                source=PatientEventSource(model_name="TEST_MODEL", model_version="TEST_VERSION"),
            )

    monkeypatch.setattr(patients_api, "PatientAssistService", FakeAssistService)
    response = TestClient(app).post("/api/v1/patients/assist", json={"text": "TEST input"})
    assert response.status_code == 200
    assert response.json()["needs_human_review"] is True
    assert response.json()["symptoms"][0]["code"] == "TEST_SYMPTOM"


@pytest.mark.asyncio
async def test_gemini_client_fails_closed_without_api_key() -> None:
    """No provider request is attempted when the Gemini key is absent."""

    settings = SimpleNamespace(
        gemini_base_url="https://example.invalid/v1beta",
        gemini_api_key=None,
        gemini_model="TEST_MODEL",
        gemini_timeout_seconds=1.0,
    )
    client = GeminiClient(settings)
    with pytest.raises(ApplicationError) as error:
        await client.extract_patient_facts("TEST input")
    assert error.value.code == "EXTERNAL_SERVICE_NOT_CONFIGURED"
