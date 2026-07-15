"""Non-clinical structural validation for patient events."""

from app.core.errors import ApplicationError
from app.modules.patient.schemas import PatientEventRequest


def validate_patient_event(event: PatientEventRequest) -> None:
    """Validate storage prerequisites without inferring medical meaning."""

    location = event.location
    if location.latitude is None and location.longitude is None and not location.address_text:
        raise ApplicationError(
            code="PATIENT_LOCATION_MISSING",
            message="환자 위치 정보가 없습니다.",
            status_code=422,
            details={"required_any_of": ["location.latitude/longitude", "location.address_text"]},
        )

