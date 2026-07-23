"""Route snapshot validity tests using isolated TEST records."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.database import Base
from app.modules.hospital.models import Hospital
from app.modules.patient.models import PatientCase
from app.modules.routing.repository import RouteSnapshotRepository
from app.modules.routing.schemas import RouteSnapshotData


def _route_data(fetched_at: datetime, source_record_id: str) -> RouteSnapshotData:
    """Build one source-backed route using TEST-only values."""

    return RouteSnapshotData(
        provider_name="TEST_ROUTE_PROVIDER",
        distance_meters=100,
        duration_seconds=60,
        traffic_summary="TEST_TRAFFIC",
        fetched_at=fetched_at,
        path=None,
        source_name="TEST_ROUTE_SOURCE",
        source_record_id=source_record_id,
        raw_payload_id=None,
        schema_version="test-route.v1",
        source_metadata={},
    )


@pytest.mark.asyncio
async def test_latest_valid_route_requires_an_explicit_validity_rule() -> None:
    """An unset max age does not silently make an unbounded route cache valid."""

    now = datetime(2026, 1, 1, 0, 10, tzinfo=UTC)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        session.add(
            PatientCase(
                incident_id="TEST_PATIENT_001",
                consciousness_status=None,
                breathing_status=None,
                bleeding_status=None,
                urgency_level=None,
                latitude=0,
                longitude=0,
                address_text=None,
                source_model_name="TEST_MODEL",
                source_model_version="TEST_VERSION",
                received_at=now,
            )
        )
        session.add(
            Hospital(
                hospital_id="TEST_HOSPITAL_001",
                hospital_name="TEST_HOSPITAL_NAME",
                hospital_type_code=None,
                address=None,
                latitude=0,
                longitude=0,
                phone=None,
                source_name="TEST_HOSPITAL_SOURCE",
                source_record_id="TEST_HOSPITAL_RECORD",
                raw_payload_id=None,
                schema_version="test-hospital.v1",
                source_updated_at=now,
            )
        )
        await session.flush()
        repository = RouteSnapshotRepository(session)
        await repository.save_snapshot(
            "TEST_PATIENT_001",
            "TEST_HOSPITAL_001",
            _route_data(now - timedelta(seconds=60), "TEST_ROUTE_UNBOUNDED"),
        )
        assert (
            await repository.get_latest_valid(
                "TEST_PATIENT_001",
                "TEST_HOSPITAL_001",
                None,
                now=now,
            )
            is None
        )

        recent = await repository.get_latest_valid(
            "TEST_PATIENT_001",
            "TEST_HOSPITAL_001",
            300,
            now=now,
        )
        assert recent is not None
        assert recent.source_record_id == "TEST_ROUTE_UNBOUNDED"

        await repository.save_snapshot(
            "TEST_PATIENT_001",
            "TEST_HOSPITAL_001",
            _route_data(now - timedelta(seconds=30), "TEST_ROUTE_EXPLICIT_EXPIRY"),
            expires_at=now + timedelta(seconds=30),
        )
        explicit = await repository.get_latest_valid(
            "TEST_PATIENT_001",
            "TEST_HOSPITAL_001",
            None,
            now=now,
        )
        assert explicit is not None
        assert explicit.source_record_id == "TEST_ROUTE_EXPLICIT_EXPIRY"

    await engine.dispose()
