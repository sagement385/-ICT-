"""Structural validation for normalized hospital records."""

from app.core.errors import ApplicationError
from app.modules.hospital.models import Hospital


def validate_hospital_record(hospital: Hospital) -> None:
    """Reject incomplete coordinate pairs without inferring capabilities."""

    if (hospital.latitude is None) != (hospital.longitude is None):
        raise ApplicationError(
            code="HOSPITAL_LOCATION_INCOMPLETE",
            message="병원 좌표가 불완전합니다.",
            status_code=422,
            details={"hospital_id": hospital.hospital_id},
        )

