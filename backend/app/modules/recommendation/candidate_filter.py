"""Candidate filter interface with no unapproved clinical defaults."""

from typing import TYPE_CHECKING

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
        """Return candidates unchanged until a verified filter policy exists."""

        del patient, policy
        return list(hospitals)

