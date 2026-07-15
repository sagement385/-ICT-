"""Candidate filter for geography only; clinical exclusions remain policy-owned."""

from typing import TYPE_CHECKING

from app.core.config import get_settings
from app.modules.hospital.geo import distance_km
from app.modules.hospital.models import Hospital
from app.modules.patient.schemas import PatientEventRequest

if TYPE_CHECKING:
    from app.modules.recommendation.policy_repository import PolicyBundle


class CandidateFilter:
    """Apply only policy-defined filters after clinical criteria are approved."""

    def filter(
        self,
        patient: PatientEventRequest,
        hospitals: list[Hospital],
        policy: "PolicyBundle | None",
    ) -> list[Hospital]:
        """Limit candidates by the configured 5-10 km geographic search radius."""

        del policy
        if patient.location.latitude is None or patient.location.longitude is None:
            return []
        radius_km = get_settings().candidate_radius_km
        return [
            hospital
            for hospital in hospitals
            if hospital.latitude is not None
            and hospital.longitude is not None
            and distance_km(
                patient.location.latitude,
                patient.location.longitude,
                hospital.latitude,
                hospital.longitude,
            ) <= radius_km
        ]
