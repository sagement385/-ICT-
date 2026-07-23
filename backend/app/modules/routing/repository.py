"""Database-only repository for route snapshots."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
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
        """Compatibility wrapper for saving one snapshot without explicit expiry."""

        return await self.save_snapshot(
            incident_id,
            hospital_id,
            route,
            recommendation_run_id=recommendation_run_id,
        )

    async def get_latest_valid(
        self,
        incident_id: str,
        hospital_id: str,
        max_age_seconds: int | None,
        *,
        now: datetime | None = None,
    ) -> RouteSnapshot | None:
        """Return the newest valid snapshot without assuming validity when no rule exists."""

        if max_age_seconds is not None and max_age_seconds < 0:
            raise ValueError("max_age_seconds must be non-negative")
        reference_time = now or datetime.now(UTC)
        statement = select(RouteSnapshot).where(
            RouteSnapshot.incident_id == incident_id,
            RouteSnapshot.hospital_id == hospital_id,
        )
        if max_age_seconds is None:
            statement = statement.where(
                RouteSnapshot.expires_at.is_not(None),
                RouteSnapshot.expires_at > reference_time,
            )
        else:
            statement = statement.where(
                RouteSnapshot.fetched_at
                >= reference_time - timedelta(seconds=max_age_seconds),
                or_(
                    RouteSnapshot.expires_at.is_(None),
                    RouteSnapshot.expires_at > reference_time,
                ),
            )
        statement = statement.order_by(RouteSnapshot.fetched_at.desc()).limit(1)
        return (await self.session.execute(statement)).scalars().first()

    async def save_snapshot(
        self,
        incident_id: str,
        hospital_id: str,
        route: RouteSnapshotData,
        *,
        recommendation_run_id: str | None = None,
        expires_at: datetime | None = None,
    ) -> RouteSnapshot:
        """Add one immutable normalized provider snapshot to the current transaction."""

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
            expires_at=expires_at,
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

    @staticmethod
    def to_data(row: RouteSnapshot) -> RouteSnapshotData:
        """Convert a persisted route into the provider-neutral contract."""

        return RouteSnapshotData(
            provider_name=row.provider_name,
            distance_meters=row.distance_meters,
            duration_seconds=row.duration_seconds,
            traffic_summary=row.traffic_summary,
            fetched_at=row.fetched_at,
            path=(
                [(float(point[0]), float(point[1])) for point in row.path_json]
                if row.path_json is not None
                else None
            ),
            source_name=row.source_name,
            source_record_id=row.source_record_id,
            raw_payload_id=row.raw_payload_id,
            schema_version=row.schema_version,
            source_metadata=dict(row.source_metadata_json or {}),
        )
