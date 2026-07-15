"""Patient ingestion structural validation stage."""

from app.modules.patient.schemas import PatientEventRequest
from app.modules.patient.validator import validate_patient_event


def validate(event: PatientEventRequest) -> PatientEventRequest:
    """Validate storage prerequisites and return the same event."""

    validate_patient_event(event)
    return event

