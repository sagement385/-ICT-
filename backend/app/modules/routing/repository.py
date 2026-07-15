"""Database-only repository for route snapshots."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.routing.models import RouteSnapshot
from app.modules.routing.schemas import RouteSnapshotData


class RouteSnapshotRepository:
    """Persist and read route snapshots without calling a route provider."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        incident_id: str,
        hospital_id: str,
        route: RouteSnapshotData,
        *,
        recommendation_run_id: str | None = None,
    ) -> RouteSnapshot:
        """Add one normalized provider snapshot to the current transaction."""

        row = RouteSnapshot(
            incident_id=incident_id,
            hospital_id=hospital_id,
            recommendation_run_id=recommendation_run_id,
            provider_name=route.provider_name,
            distance_meters=route.distance_meters,
            duration_seconds=route.duration_seconds,
            traffic_summary=route.traffic_summary,
            path_json=[list(point) for point in route.path] if route.path is not None else None,
            source_name=route.source_name,
            source_record_id=route.source_record_id,
            raw_payload_id=route.raw_payload_id,
            schema_version=route.schema_version,
            source_metadata_json=route.source_metadata,
            fetched_at=route.fetched_at,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_for_run(self, recommendation_run_id: str) -> dict[str, RouteSnapshot]:
        """Return the persisted route for each hospital in one recommendation run."""

        statement = (
            select(RouteSnapshot)
            .where(RouteSnapshot.recommendation_run_id == recommendation_run_id)
            .order_by(RouteSnapshot.fetched_at.asc())
        )
        rows = list((await self.session.execute(statement)).scalars())
        return {row.hospital_id: row for row in rows}
