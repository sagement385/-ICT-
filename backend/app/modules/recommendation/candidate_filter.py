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
        patient_latitude = patient.location.latitude
        patient_longitude = patient.location.longitude
        if patient_latitude is None or patient_longitude is None:
            return []
        radius_km = get_settings().candidate_radius_km
        candidates: list[tuple[float, Hospital]] = []
        for hospital in hospitals:
            hospital_latitude = hospital.latitude
            hospital_longitude = hospital.longitude
            if hospital_latitude is None or hospital_longitude is None:
                continue
            candidate_distance = distance_km(
                patient_latitude,
                patient_longitude,
                hospital_latitude,
                hospital_longitude,
            )
            if candidate_distance <= radius_km:
                candidates.append((candidate_distance, hospital))
        return [hospital for _, hospital in sorted(candidates, key=lambda item: item[0])]
