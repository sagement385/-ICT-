"""Stored-incident routing with bounded provider calls and cache reuse."""

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import ApplicationError
from app.modules.hospital.repository import HospitalRepository
from app.modules.patient.repository import PatientRepository
from app.modules.routing.provider import RoutingProvider
from app.modules.routing.repository import RouteSnapshotRepository
from app.modules.routing.schemas import (
    RouteBatchError,
    RouteBatchItem,
    RouteBatchQuery,
    RouteBatchResponse,
    RouteQuery,
    RouteSnapshotData,
)


class RoutingService:
    """Use canonical DB coordinates, reuse valid snapshots, and bound concurrency."""

    def __init__(
        self,
        session: AsyncSession,
        provider: RoutingProvider,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.provider = provider
        self.settings = settings or get_settings()
        self.patient_repository = PatientRepository(session)
        self.hospital_repository = HospitalRepository(session)
        self.route_repository = RouteSnapshotRepository(session)

    async def get_route(self, query: RouteQuery) -> RouteSnapshotData:
        """Fetch one provider route for the explicit diagnostic endpoint."""

        return await self.provider.get_route(query)

    async def get_batch(
        self,
        query: RouteBatchQuery,
        *,
        recommendation_run_id: str | None = None,
    ) -> RouteBatchResponse:
        """Return cached or freshly fetched routes for canonical incident/hospital data."""

        patient_record = await self.patient_repository.get_case(query.incident_id)
        if patient_record is None:
            raise ApplicationError(
                code="PATIENT_NOT_FOUND",
                message="경로를 조회할 환자 사건을 찾을 수 없습니다.",
                status_code=404,
                details={"incident_id": query.incident_id},
            )
        patient, _ = patient_record
        if patient.latitude is None or patient.longitude is None:
            raise ApplicationError(
                code="PATIENT_LOCATION_REQUIRED",
                message="실제 경로를 조회하려면 저장된 환자 좌표가 필요합니다.",
                details={"incident_id": query.incident_id},
            )
        origin_latitude = patient.latitude
        origin_longitude = patient.longitude

        requested_ids = query.unique_hospital_ids
        hospitals = await self.hospital_repository.get_emergency_hospitals_by_ids(requested_ids)
        errors = [
            RouteBatchError(
                hospital_id=hospital_id,
                code="HOSPITAL_NOT_ELIGIBLE_FOR_ROUTING",
                message="활성 공식 응급의료기관으로 연결된 병원이 아닙니다.",
            )
            for hospital_id in requested_ids
            if hospital_id not in hospitals
        ]
        routes: list[RouteBatchItem] = []
        misses: list[str] = []
        for hospital_id in requested_ids:
            hospital = hospitals.get(hospital_id)
            if hospital is None:
                continue
            if hospital.latitude is None or hospital.longitude is None:
                errors.append(
                    RouteBatchError(
                        hospital_id=hospital_id,
                        code="HOSPITAL_LOCATION_UNAVAILABLE",
                        message="병원 원본 좌표가 없어 경로를 조회할 수 없습니다.",
                    )
                )
                continue
            cached = await self.route_repository.get_latest_valid(
                query.incident_id,
                hospital_id,
                self.settings.route_data_max_age_seconds,
            )
            if cached is not None:
                cached_data = self.route_repository.to_data(cached)
                routes.append(
                    RouteBatchItem(
                        hospital_id=hospital_id,
                        route=cached_data,
                        cache_status="hit",
                    )
                )
                if recommendation_run_id is not None:
                    await self.route_repository.save_snapshot(
                        query.incident_id,
                        hospital_id,
                        cached_data,
                        recommendation_run_id=recommendation_run_id,
                        expires_at=cached.expires_at,
                    )
            else:
                misses.append(hospital_id)

        # End read transactions before waiting on external network calls.
        await self.session.commit()
        semaphore = asyncio.Semaphore(self.settings.routing_max_concurrency)

        async def fetch_one(hospital_id: str) -> RouteBatchItem | RouteBatchError:
            hospital = hospitals[hospital_id]
            if hospital.latitude is None or hospital.longitude is None:
                raise AssertionError("coordinate availability was checked before routing")
            route_query = RouteQuery(
                origin_latitude=origin_latitude,
                origin_longitude=origin_longitude,
                destination_latitude=hospital.latitude,
                destination_longitude=hospital.longitude,
            )
            try:
                async with semaphore:
                    route = await self.provider.get_route(route_query)
                return RouteBatchItem(
                    hospital_id=hospital_id,
                    route=route,
                    cache_status="miss",
                )
            except ApplicationError as error:
                return RouteBatchError(
                    hospital_id=hospital_id,
                    code=error.code,
                    message=error.message,
                )

        fetched = await asyncio.gather(*(fetch_one(hospital_id) for hospital_id in misses))
        for item in fetched:
            if isinstance(item, RouteBatchError):
                errors.append(item)
                continue
            routes.append(item)
            expires_at = (
                item.route.fetched_at
                + timedelta(seconds=self.settings.route_data_max_age_seconds)
                if self.settings.route_data_max_age_seconds is not None
                else None
            )
            await self.route_repository.save_snapshot(
                query.incident_id,
                item.hospital_id,
                item.route,
                recommendation_run_id=recommendation_run_id,
                expires_at=expires_at,
            )
        if recommendation_run_id is not None or any(
            item.cache_status == "miss" for item in routes
        ):
            await self.session.commit()

        order = {hospital_id: index for index, hospital_id in enumerate(requested_ids)}
        routes.sort(key=lambda item: order[item.hospital_id])
        errors.sort(key=lambda item: order[item.hospital_id])
        return RouteBatchResponse(
            routes=routes,
            errors=errors,
            generated_at=datetime.now(UTC),
        )
