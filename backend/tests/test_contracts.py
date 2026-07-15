"""JSON Schema and request validation tests using only test fixtures."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from app.modules.patient.schemas import PatientEventRequest

ROOT = Path(__file__).resolve().parents[2]


def test_patient_event_schema_accepts_test_fixture() -> None:
    """The patient contract accepts a minimal redacted test event."""

    schema = json.loads((ROOT / "contracts/patient-event.schema.json").read_text(encoding="utf-8"))
    fixture = json.loads((ROOT / "backend/tests/fixtures/patient-event-test.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(fixture)


def test_patient_request_rejects_unpaired_coordinates() -> None:
    """A half coordinate pair is rejected before storage."""

    payload = {
        "incident_id": "TEST_PATIENT_001",
        "observed_at": "2026-01-01T00:00:00Z",
        "location": {"latitude": 1.0, "longitude": None, "address_text": None},
        "symptoms": [],
        "source": {"model_name": "TEST_MODEL", "model_version": "TEST_VERSION"},
    }
    with pytest.raises(ValidationError):
        PatientEventRequest.model_validate(payload)

