"""Patient normalization stage reserved for approved contract changes."""

from app.modules.patient.schemas import PatientEventRequest


def normalize(event: PatientEventRequest) -> PatientEventRequest:
    """Return the contract unchanged until normalization rules are approved."""

    return event

