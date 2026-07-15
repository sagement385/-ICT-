"""Fail-closed recommendation orchestration."""

from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError
from app.modules.hospital.models import Hospital
from app.modules.hospital.repository import HospitalRepository
from app.modules.patient.repository import PatientRepository
from app.modules.patient.schemas import (
    PatientEventRequest,
    PatientEventSource,
    PatientLocation,
    PatientSymptomInput,
)
from app.modules.recommendation.candidate_filter import CandidateFilter
from app.modules.recommendation.feature_builder import FeatureBuilder
from app.modules.recommendation.models import RecommendationResult, RecommendationRun
from app.modules.recommendation.policy_repository import RecommendationPolicyRepository
from app.modules.recommendation.ranking_service import RankingService
from app.modules.recommendation.schemas import RecommendationResultResponse
from app.modules.recommendation.score_calculator import ScoreCalculator
from app.modules.routing.schemas import RouteQuery, RouteSnapshotData


class RealtimeStatusProvider(Protocol):
    """Boundary for loading source-backed hospital realtime status."""

    async def load(self, hospital_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Load status records without inventing unavailable values."""


class RouteDataProvider(Protocol):
    """Boundary for a real route provider."""

    async def get_route(self, query: RouteQuery) -> RouteSnapshotData:
        """Fetch a route snapshot from a configured provider."""


class RecommendationService:
    """Run the documented sequence and stop at the first missing dependency."""

    def __init__(
        self,
        session: AsyncSession,
        candidate_filter: CandidateFilter | None = None,
        feature_builder: FeatureBuilder | None = None,
        score_calculator: ScoreCalculator | None = None,
        ranking_service: RankingService | None = None,
        realtime_provider: RealtimeStatusProvider | None = None,
        route_provider: RouteDataProvider | None = None,
    ) -> None:
        self.session = session
        self.patient_repository = PatientRepository(session)
        self.hospital_repository = HospitalRepository(session)
        self.policy_repository = RecommendationPolicyRepository(session)
        self.candidate_filter = candidate_filter or CandidateFilter()
        self.feature_builder = feature_builder or FeatureBuilder()
        self.score_calculator = score_calculator or ScoreCalculator()
        self.ranking_service = ranking_service or RankingService()
        self.realtime_provider = realtime_provider
        self.route_provider = route_provider

    async def run(self, incident_id: str, limit: int) -> RecommendationResultResponse:
        """Execute patient -> hospital -> realtime -> route -> policy -> score workflow."""

        record = await self.patient_repository.get_case(incident_id)
        if record is None:
            raise ApplicationError(
                code="PATIENT_NOT_FOUND",
                message="해당 incident_id의 환자 정보가 없습니다.",
                status_code=404,
                details={"incident_id": incident_id},
            )
        case, symptoms = record
        patient = self._to_patient_event(case, symptoms)

        hospitals = await self.hospital_repository.list_all()
        if not hospitals:
            raise ApplicationError(
                code="HOSPITAL_CANDIDATES_EMPTY",
                message="추천에 사용할 병원 데이터가 없습니다.",
                status_code=503,
                details={},
            )

        hospital_ids = [hospital.hospital_id for hospital in hospitals]
        if self.realtime_provider is None:
            raise ApplicationError(
                code="HOSPITAL_REALTIME_STATUS_UNAVAILABLE",
                message="병원 실시간 수용 상태 제공자가 설정되지 않았습니다.",
                details={},
            )
        realtime_status = await self.realtime_provider.load(hospital_ids)

        if self.route_provider is None:
            raise ApplicationError(
                code="ROUTE_DATA_UNAVAILABLE",
                message="실제 이동시간 제공자가 설정되지 않았습니다.",
                details={},
            )
        route_data = await self._load_routes(patient, hospitals)

        policy = await self.policy_repository.get_active_policy()
        candidates = self.candidate_filter.filter(patient, hospitals, policy)
        features = self.feature_builder.build(patient, candidates, route_data, realtime_status)
        scored = self.score_calculator.calculate(features, policy.weights)
        ranked = self.ranking_service.rank(list(scored.values()), limit)
        del ranked

        raise ApplicationError(
            code="RECOMMENDATION_PERSISTENCE_NOT_IMPLEMENTED",
            message="추천 결과 저장 단계가 아직 구현되지 않았습니다.",
            details={"policy_id": policy.policy.id},
        )

    async def latest(self, incident_id: str) -> RecommendationResultResponse:
        """Fetch the latest persisted result; never manufacture an empty result."""

        statement = (
            select(RecommendationResult)
            .join(RecommendationRun, RecommendationRun.id == RecommendationResult.recommendation_run_id)
            .where(RecommendationRun.incident_id == incident_id)
            .order_by(RecommendationResult.created_at.desc())
        )
        record = (await self.session.execute(statement)).scalars().first()
        if record is None:
            raise ApplicationError(
                code="RECOMMENDATION_RESULT_NOT_FOUND",
                message="저장된 추천 결과가 없습니다.",
                status_code=404,
                details={"incident_id": incident_id},
            )
        raise ApplicationError(
            code="RECOMMENDATION_RESULT_SERIALIZATION_NOT_IMPLEMENTED",
            message="저장된 추천 결과의 계약 변환이 아직 구현되지 않았습니다.",
            details={"result_id": record.id},
        )

    async def _load_routes(
        self,
        patient: PatientEventRequest,
        hospitals: list[Hospital],
    ) -> dict[str, RouteSnapshotData]:
        """Load routes only when both incident and hospital coordinates exist."""

        if patient.location.latitude is None or patient.location.longitude is None:
            raise ApplicationError(
                code="ROUTE_DATA_UNAVAILABLE",
                message="환자 좌표가 없어 실제 이동시간을 조회할 수 없습니다.",
                details={},
            )
        provider = self.route_provider
        if provider is None:
            raise ApplicationError(
                code="ROUTE_DATA_UNAVAILABLE",
                message="실제 이동시간 제공자가 설정되지 않았습니다.",
                details={},
            )
        routes: dict[str, RouteSnapshotData] = {}
        for hospital in hospitals:
            if hospital.latitude is None or hospital.longitude is None:
                continue
            query = RouteQuery(
                origin_latitude=patient.location.latitude,
                origin_longitude=patient.location.longitude,
                destination_latitude=hospital.latitude,
                destination_longitude=hospital.longitude,
            )
            routes[hospital.hospital_id] = await provider.get_route(query)
        if not routes:
            raise ApplicationError(
                code="ROUTE_DATA_UNAVAILABLE",
                message="병원 좌표가 없어 실제 이동시간을 조회할 수 없습니다.",
                details={},
            )
        return routes

    @staticmethod
    def _to_patient_event(case: Any, symptoms: list[Any]) -> PatientEventRequest:
        """Convert stored records into the cross-module patient contract."""

        return PatientEventRequest(
            incident_id=case.incident_id,
            observed_at=case.received_at,
            location=PatientLocation(
                latitude=case.latitude,
                longitude=case.longitude,
                address_text=case.address_text,
            ),
            symptoms=[
                PatientSymptomInput(
                    code=item.symptom_code,
                    label=item.symptom_label,
                    confidence=item.confidence,
                )
                for item in symptoms
            ],
            consciousness_status=case.consciousness_status,
            breathing_status=case.breathing_status,
            bleeding_status=case.bleeding_status,
            urgency_level=case.urgency_level,
            source=PatientEventSource(
                model_name=case.source_model_name,
                model_version=case.source_model_version,
            ),
        )
