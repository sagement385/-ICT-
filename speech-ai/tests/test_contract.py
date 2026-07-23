"""Speech-side patient contract tests using only redacted TEST data."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas import PatientEvent

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "patient-event-test.json"


def test_patient_event_fixture_is_valid() -> None:
    """The Speech AI boundary accepts the shared patient-event shape."""

    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    event = PatientEvent.model_validate(payload)
    assert event.incident_id == "TEST_PATIENT_001"


def test_patient_event_rejects_half_coordinate_pair() -> None:
    """Speech AI cannot emit only one coordinate from the pair."""

    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    payload["location"]["latitude"] = 0.0
    with pytest.raises(ValidationError):
        PatientEvent.model_validate(payload)
