"""Fail-closed recommendation orchestration and persistence."""

from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.integrations.naver_maps.directions_client import NaverDirectionsClient
from app.modules.hospital.models import Hospital, HospitalRealtimeStatus
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
from app.modules.recommendation.models import (
    RecommendationPolicy,
    RecommendationResult,
    RecommendationRun,
)
from app.modules.recommendation.policy_repository import (
    PolicyBundle,
    RecommendationPolicyRepository,
)
from app.modules.recommendation.ranking_service import RankingService
from app.modules.recommendation.schemas import (
    PolicyResponse,
    RecommendationResultResponse,
    RecommendedHospitalResponse,
    TravelTimeResponse,
)
from app.modules.recommendation.score_calculator import ScoreCalculator
from app.modules.routing.models import RouteSnapshot
from app.modules.routing.provider import NaverRoutingProvider
from app.modules.routing.repository import RouteSnapshotRepository
from app.modules.routing.schemas import RouteQuery, RouteSnapshotData


class RealtimeStatusProvider(Protocol):
    """Boundary for loading source-backed hospital realtime status."""

    async def load(self, hospital_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Load status records without inventing unavailable values."""


class RouteDataProvider(Protocol):
    """Boundary for a real route provider."""

    async def get_route(self, query: RouteQuery) -> RouteSnapshotData:
        """Fetch a route snapshot from a configured provider."""


class DatabaseRealtimeStatusProvider:
    """Load the latest source-backed realtime row linked to each hospital."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def load(self, hospital_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Return available rows and leave missing hospitals explicitly absent."""

        statement = (
            select(HospitalRealtimeStatus)
            .where(HospitalRealtimeStatus.hospital_id.in_(hospital_ids))
            .order_by(
                HospitalRealtimeStatus.hospital_id,
                HospitalRealtimeStatus.fetched_at.asc(),
            )
        )
        rows = list((await self.session.execute(statement)).scalars())
        return {
            row.hospital_id: {
                "acceptance_status": row.acceptance_status,
                "available_beds": row.available_beds,
                "source_name": row.source_name,
                "source_record_id": row.source_record_id,
                "raw_payload_id": row.raw_payload_id,
                "schema_version": row.schema_version,
                "source_updated_at": row.source_updated_at,
                "fetched_at": row.fetched_at,
            }
            for row in rows
        }


class RecommendationService:
    """Run policy-controlled recommendation stages and persist an audit trail."""

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
        self.route_repository = RouteSnapshotRepository(session)
        self.candidate_filter = candidate_filter or CandidateFilter()
        self.feature_builder = feature_builder or FeatureBuilder()
        self.score_calculator = score_calculator or ScoreCalculator()
        self.ranking_service = ranking_service or RankingService()
        self.realtime_provider: RealtimeStatusProvider = (
            realtime_provider or DatabaseRealtimeStatusProvider(session)
        )
        self.route_provider: RouteDataProvider = route_provider or NaverRoutingProvider(
            NaverDirectionsClient()
        )

    async def run(self, incident_id: str, limit: int) -> RecommendationResultResponse:
        """Execute the workflow while retaining fail-closed attempts in the database."""

        if not 1 <= limit <= 3:
            raise ApplicationError(
                code="RECOMMENDATION_LIMIT_INVALID",
                message="추천 결과 개수는 1개에서 3개 사이여야 합니다.",
                status_code=422,
                details={"limit": limit},
            )
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

        run = RecommendationRun(
            incident_id=incident_id,
            policy_id=None,
            started_at=datetime.now(UTC),
            completed_at=None,
            status="started",
            error_code=None,
            warnings_json=[],
        )
        self.session.add(run)
        await self.session.commit()

        warnings: list[str] = []
        try:
            if patient.location.latitude is None or patient.location.longitude is None:
                raise ApplicationError(
                    code="PATIENT_LOCATION_REQUIRED",
                    message="병원 후보와 실제 경로를 조회하려면 환자 좌표가 필요합니다.",
                    details={"incident_id": incident_id},
                )

            hospitals = await self.hospital_repository.list_all()
            if not hospitals:
                raise ApplicationError(
                    code="HOSPITAL_CANDIDATES_EMPTY",
                    message="추천에 사용할 병원 데이터가 없습니다.",
                    details={},
                )

            hospitals = self.candidate_filter.filter(patient, hospitals, None)
            if not hospitals:
                raise ApplicationError(
                    code="HOSPITAL_CANDIDATES_EMPTY",
                    message="설정된 반경 안에 좌표가 있는 병원 후보가 없습니다.",
                    details={"radius_km": get_settings().candidate_radius_km},
                )

            settings = get_settings()
            if len(hospitals) > settings.recommendation_route_candidate_limit:
                hospitals = hospitals[: settings.recommendation_route_candidate_limit]
                warnings.append("CANDIDATES_TRUNCATED_FOR_ROUTE_QUOTA")

            # Policy preflight intentionally precedes quota-consuming provider calls.
            policy = await self.policy_repository.get_active_policy()
            run.policy_id = policy.policy.id
            hospital_ids = [hospital.hospital_id for hospital in hospitals]
            realtime_status = await self.realtime_provider.load(hospital_ids)
            route_data, route_warnings = await self._load_routes(patient, hospitals)
            warnings.extend(route_warnings)

            candidates = self.candidate_filter.filter(patient, hospitals, policy)
            features = self.feature_builder.build(
                patient,
                candidates,
                route_data,
                realtime_status,
            )
            scored = self.score_calculator.calculate(features, policy.weights)
            ranked = self.ranking_service.rank(list(scored.values()), limit)
            if not ranked:
                raise ApplicationError(
                    code="HOSPITAL_CANDIDATES_EMPTY",
                    message="활성 정책을 통과한 병원 후보가 없습니다.",
                    details={"evaluated_hospital_count": len(scored)},
                )

            for hospital_id, route in route_data.items():
                await self.route_repository.add(
                    incident_id,
                    hospital_id,
                    route,
                    recommendation_run_id=run.id,
                )

            result_rows: list[RecommendationResult] = []
            for item in ranked:
                result_row = RecommendationResult(
                    recommendation_run_id=run.id,
                    hospital_id=str(item["hospital_id"]),
                    rank=int(item["rank"]),
                    total_score=float(item["total_score"]),
                    score_breakdown_json=dict(item["score_breakdown"]),
                    exclusion_reasons_json=list(item["exclusion_reasons"]),
                    recommendation_reasons_json=list(item["recommendation_reasons"]),
                    data_freshness_json=dict(item["freshness"]),
                    source_provenance_json=dict(item["source_provenance"]),
                )
                self.session.add(result_row)
                result_rows.append(result_row)
                warnings.extend(item.get("warnings") or [])

            run.status = "completed"
            run.completed_at = datetime.now(UTC)
            run.error_code = None
            run.warnings_json = sorted(set(warnings))
            await self.session.commit()
            return self._response_from_scored(run, policy, ranked)
        except ApplicationError as error:
            await self._mark_failed(run, error.code, warnings)
            raise
        except Exception:
            await self._mark_failed(run, "RECOMMENDATION_INTERNAL_ERROR", warnings)
            raise

    async def latest(self, incident_id: str) -> RecommendationResultResponse:
        """Return the latest completed persisted run and its exact historical policy."""

        patient = await self.patient_repository.get_case(incident_id)
        if patient is None:
            raise ApplicationError(
                code="PATIENT_NOT_FOUND",
                message="해당 incident_id의 환자 정보가 없습니다.",
                status_code=404,
                details={"incident_id": incident_id},
            )
        statement = (
            select(RecommendationRun)
            .where(
                RecommendationRun.incident_id == incident_id,
                RecommendationRun.status == "completed",
            )
            .order_by(RecommendationRun.completed_at.desc(), RecommendationRun.started_at.desc())
        )
        run = (await self.session.execute(statement)).scalars().first()
        if run is None:
            raise ApplicationError(
                code="RECOMMENDATION_RESULT_NOT_FOUND",
                message="저장된 추천 결과가 없습니다.",
                status_code=404,
                details={"incident_id": incident_id},
            )
        if run.policy_id is None:
            raise ApplicationError(
                code="RECOMMENDATION_RESULT_INTEGRITY_ERROR",
                message="저장된 추천 실행에 정책 식별자가 없습니다.",
                details={"recommendation_run_id": run.id},
            )
        policy = await self.session.get(RecommendationPolicy, run.policy_id)
        if policy is None:
            raise ApplicationError(
                code="RECOMMENDATION_RESULT_INTEGRITY_ERROR",
                message="저장된 추천 정책을 조회할 수 없습니다.",
                details={"recommendation_run_id": run.id},
            )
        results = list(
            (
                await self.session.execute(
                    select(RecommendationResult)
                    .where(RecommendationResult.recommendation_run_id == run.id)
                    .order_by(RecommendationResult.rank.asc())
                )
            ).scalars()
        )
        if not results:
            raise ApplicationError(
                code="RECOMMENDATION_RESULT_INTEGRITY_ERROR",
                message="완료된 추천 실행에 병원 결과가 없습니다.",
                details={"recommendation_run_id": run.id},
            )
        hospital_ids = [result.hospital_id for result in results]
        hospitals = {
            hospital.hospital_id: hospital
            for hospital in (
                await self.session.execute(select(Hospital).where(Hospital.hospital_id.in_(hospital_ids)))
            ).scalars()
        }
        routes = await self.route_repository.list_for_run(run.id)
        recommended: list[RecommendedHospitalResponse] = []
        warnings = list(run.warnings_json)
        for result in results:
            hospital = hospitals.get(result.hospital_id)
            if hospital is None:
                raise ApplicationError(
                    code="RECOMMENDATION_RESULT_INTEGRITY_ERROR",
                    message="추천 결과의 병원 정보를 조회할 수 없습니다.",
                    details={"hospital_id": result.hospital_id},
                )
            route = routes.get(result.hospital_id)
            recommended.append(
                RecommendedHospitalResponse(
                    rank=result.rank,
                    hospital_id=hospital.hospital_id,
                    hospital_name=hospital.hospital_name,
                    location={
                        "latitude": hospital.latitude,
                        "longitude": hospital.longitude,
                        "address": hospital.address,
                    },
                    total_score=result.total_score,
                    score_breakdown=result.score_breakdown_json,
                    travel_time=self._travel_time_from_row(route),
                    recommendation_reasons=result.recommendation_reasons_json,
                    data_freshness=result.data_freshness_json,
                )
            )
            if route is None:
                warnings.append("ROUTE_DATA_UNAVAILABLE")
        return RecommendationResultResponse(
            incident_id=run.incident_id,
            recommendation_run_id=run.id,
            generated_at=run.completed_at or run.started_at,
            policy=PolicyResponse(
                policy_name=policy.policy_name,
                policy_version=policy.policy_version,
            ),
            recommended_hospitals=recommended,
            warnings=sorted(set(warnings)),
        )

    async def _load_routes(
        self,
        patient: PatientEventRequest,
        hospitals: list[Hospital],
    ) -> tuple[dict[str, RouteSnapshotData], list[str]]:
        """Load independent provider routes and retain explicit partial failures."""

        if patient.location.latitude is None or patient.location.longitude is None:
            return {}, ["ROUTE_DATA_UNAVAILABLE"]
        routes: dict[str, RouteSnapshotData] = {}
        warnings: list[str] = []
        for hospital in hospitals:
            if hospital.latitude is None or hospital.longitude is None:
                warnings.append("ROUTE_DATA_UNAVAILABLE")
                continue
            query = RouteQuery(
                origin_latitude=patient.location.latitude,
                origin_longitude=patient.location.longitude,
                destination_latitude=hospital.latitude,
                destination_longitude=hospital.longitude,
            )
            try:
                routes[hospital.hospital_id] = await self.route_provider.get_route(query)
            except ApplicationError as error:
                warnings.append(error.code)
        if not routes:
            warnings.append("ROUTE_DATA_UNAVAILABLE")
        return routes, sorted(set(warnings))

    async def _mark_failed(
        self,
        run: RecommendationRun,
        error_code: str,
        warnings: list[str],
    ) -> None:
        """Close a started audit row without replacing the original exception."""

        run.status = "failed"
        run.completed_at = datetime.now(UTC)
        run.error_code = error_code
        run.warnings_json = sorted(set(warnings))
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()

    @staticmethod
    def _response_from_scored(
        run: RecommendationRun,
        policy: PolicyBundle,
        ranked: list[dict[str, Any]],
    ) -> RecommendationResultResponse:
        """Serialize the same values that were persisted for this run."""

        hospitals = [
            RecommendedHospitalResponse(
                rank=int(item["rank"]),
                hospital_id=str(item["hospital_id"]),
                hospital_name=str(item["hospital_name"]),
                location=dict(item["location"]),
                total_score=float(item["total_score"]),
                score_breakdown=dict(item["score_breakdown"]),
                travel_time=(
                    TravelTimeResponse.model_validate(item["travel_time"])
                    if item.get("travel_time") is not None
                    else None
                ),
                recommendation_reasons=list(item["recommendation_reasons"]),
                data_freshness=dict(item["freshness"]),
            )
            for item in ranked
        ]
        return RecommendationResultResponse(
            incident_id=run.incident_id,
            recommendation_run_id=run.id,
            generated_at=run.completed_at or run.started_at,
            policy=PolicyResponse(
                policy_name=policy.policy.policy_name,
                policy_version=policy.policy.policy_version,
            ),
            recommended_hospitals=hospitals,
            warnings=sorted(set(run.warnings_json)),
        )

    @staticmethod
    def _travel_time_from_row(route: RouteSnapshot | None) -> TravelTimeResponse | None:
        """Convert one persisted snapshot to the public travel-time contract."""

        if route is None:
            return None
        return TravelTimeResponse(
            duration_seconds=route.duration_seconds,
            distance_meters=route.distance_meters,
            provider_name=route.provider_name,
            fetched_at=route.fetched_at,
        )

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
