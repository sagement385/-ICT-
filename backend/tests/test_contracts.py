"""JSON Schema and request validation tests using only test fixtures."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import BaseModel, ValidationError

from app.main import app
from app.modules.hospital.schemas import HospitalCandidateResponse, HospitalResponse
from app.modules.patient.schemas import PatientEventRequest
from app.modules.recommendation.schemas import (
    RecommendationRequest,
    RecommendationResultResponse,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "backend/tests/fixtures"


def load_json(path: Path) -> object:
    """Load one TEST-only JSON document."""

    return json.loads(path.read_text(encoding="utf-8"))


def validate_fixture(schema_name: str, fixture_name: str) -> object:
    """Validate a fixture with JSON Schema format checks enabled."""

    schema = load_json(ROOT / "contracts" / schema_name)
    fixture = load_json(FIXTURES / fixture_name)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(fixture)
    return fixture


def load_speech_schema_module() -> ModuleType:
    """Load the independent Speech AI schema without importing its package as backend app."""

    schema_path = ROOT / "speech-ai/app/schemas.py"
    spec = importlib.util.spec_from_file_location("speech_contract_schemas", schema_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Speech AI schema module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "schema_name",
    [
        "patient-event.schema.json",
        "hospital-summary.schema.json",
        "hospital-candidate.schema.json",
        "recommendation-request.schema.json",
        "recommendation-result.schema.json",
    ],
)
def test_contract_schema_is_valid(schema_name: str) -> None:
    """Every shared contract must be a valid JSON Schema document."""

    schema = load_json(ROOT / "contracts" / schema_name)
    Draft202012Validator.check_schema(schema)


def test_patient_event_fixture_is_shared_by_json_backend_and_speech_models() -> None:
    """The same redacted event is accepted by every Python contract boundary."""

    fixture = validate_fixture("patient-event.schema.json", "patient-event-test.json")
    PatientEventRequest.model_validate(fixture)
    speech_module = load_speech_schema_module()
    speech_module.PatientEvent.model_validate(fixture)


@pytest.mark.parametrize(
    ("schema_name", "fixture_name", "model"),
    [
        ("hospital-summary.schema.json", "hospital-summary-test.json", HospitalResponse),
        (
            "hospital-candidate.schema.json",
            "hospital-candidate-test.json",
            HospitalCandidateResponse,
        ),
        (
            "recommendation-request.schema.json",
            "recommendation-request-test.json",
            RecommendationRequest,
        ),
        (
            "recommendation-result.schema.json",
            "recommendation-result-test.json",
            RecommendationResultResponse,
        ),
    ],
)
def test_json_fixtures_match_backend_models(
    schema_name: str,
    fixture_name: str,
    model: type[BaseModel],
) -> None:
    """Shared TEST examples stay valid in JSON Schema and backend Pydantic."""

    fixture = validate_fixture(schema_name, fixture_name)
    model.model_validate(fixture)


def test_patient_request_rejects_unpaired_coordinates() -> None:
    """A half coordinate pair is rejected by JSON Schema and Pydantic."""

    payload = {
        "incident_id": "TEST_PATIENT_001",
        "observed_at": "2026-01-01T00:00:00Z",
        "location": {"latitude": 1.0, "longitude": None, "address_text": None},
        "symptoms": [],
        "consciousness_status": None,
        "breathing_status": None,
        "bleeding_status": None,
        "urgency_level": None,
        "source": {"model_name": "TEST_MODEL", "model_version": "TEST_VERSION"},
    }
    schema = load_json(ROOT / "contracts/patient-event.schema.json")
    with pytest.raises(JsonSchemaValidationError):
        Draft202012Validator(schema).validate(payload)
    with pytest.raises(ValidationError):
        PatientEventRequest.model_validate(payload)


def test_recommendation_request_rejects_duplicate_incident_id() -> None:
    """The URL path is the only incident identifier for recommendation runs."""

    payload = {"incident_id": "TEST_PATIENT_001", "limit": 3}
    schema = load_json(ROOT / "contracts/recommendation-request.schema.json")
    with pytest.raises(JsonSchemaValidationError):
        Draft202012Validator(schema).validate(payload)
    with pytest.raises(ValidationError):
        RecommendationRequest.model_validate(payload)


def test_patient_status_keys_are_required_even_when_values_are_nullable() -> None:
    """Backend and Speech AI require status keys while accepting null values."""

    payload = load_json(FIXTURES / "patient-event-test.json")
    assert isinstance(payload, dict)
    payload.pop("consciousness_status")
    schema = load_json(ROOT / "contracts/patient-event.schema.json")
    with pytest.raises(JsonSchemaValidationError):
        Draft202012Validator(schema).validate(payload)
    with pytest.raises(ValidationError):
        PatientEventRequest.model_validate(payload)
    speech_module = load_speech_schema_module()
    with pytest.raises(ValidationError):
        speech_module.PatientEvent.model_validate(payload)


def test_openapi_recommendation_body_has_no_incident_id() -> None:
    """Generated OpenAPI keeps the path identifier out of the request body."""

    request_schema = app.openapi()["components"]["schemas"]["RecommendationRequest"]
    assert set(request_schema["properties"]) == {"limit"}
