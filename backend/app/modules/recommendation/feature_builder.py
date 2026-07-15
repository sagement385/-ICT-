"""Recommendation feature interface; no guessed medical features are produced."""

from typing import Any

from app.core.errors import ApplicationError
from app.modules.hospital.models import Hospital
from app.modules.patient.schemas import PatientEventRequest
from app.modules.routing.schemas import RouteSnapshotData


class FeatureBuilder:
    """Build verified features once source schemas and policy are approved."""

    def build(
        self,
        patient: PatientEventRequest,
        hospitals: list[Hospital],
        route_data: dict[str, RouteSnapshotData],
        realtime_status: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """Fail closed until feature definitions are backed by approved data."""

        del patient, hospitals, route_data, realtime_status
        raise ApplicationError(
            code="RECOMMENDATION_FEATURES_NOT_IMPLEMENTED",
            message="검증된 추천 특징값 정의가 아직 없습니다.",
            details={},
        )

