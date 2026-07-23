"""Database realtime provider tests for one latest row per hospital."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.database import Base
from app.modules.hospital.models import Hospital, HospitalRealtimeStatus
from app.modules.recommendation.feature_builder import FeatureBuilder
from app.modules.recommendation.recommendation_service import (
    DatabaseRealtimeStatusProvider,
)


def _hospital(hospital_id: str, now: datetime) -> Hospital:
    """Build one TEST-only canonical hospital."""

    return Hospital(
        hospital_id=hospital_id,
        hospital_name=f"{hospital_id}_NAME",
        hospital_type_code=None,
        address=None,
        latitude=None,
        longitude=None,
        phone=None,
        source_name="TEST_HOSPITAL_SOURCE",
        source_record_id=hospital_id,
        raw_payload_id=None,
        schema_version="test-hospital.v1",
        source_updated_at=now,
    )


def _status(
    hospital_id: str,
    source_record_id: str,
    source_updated_at: datetime | None,
    fetched_at: datetime,
    source_timezone: str | None = None,
) -> HospitalRealtimeStatus:
    """Build one TEST-only realtime snapshot."""

    return HospitalRealtimeStatus(
        hospital_id=hospital_id,
        acceptance_status=None,
        available_beds=None,
        source_name="TEST_NEMC",
        source_record_id=source_record_id,
        raw_payload_id=None,
        schema_version="test-nemc.v1",
        source_updated_at=source_updated_at,
        source_updated_at_raw=(
            source_updated_at.strftime("%Y%m%d%H%M%S")
            if source_updated_at is not None
            else None
        ),
        source_timezone=(
            source_timezone
            if source_timezone is not None
            else ("Asia/Seoul" if source_updated_at is not None else "unknown")
        ),
        fetched_at=fetched_at,
    )


def test_unknown_source_timezone_uses_fetch_time_for_freshness() -> None:
    """A legacy or unverified source timestamp cannot define freshness."""

    fetched_at = datetime(2026, 1, 1, tzinfo=UTC)
    observed_at = FeatureBuilder._status_observed_at(
        {
            "source_updated_at": fetched_at + timedelta(days=1),
            "source_timezone": "unknown",
            "fetched_at": fetched_at,
        }
    )
    assert observed_at == fetched_at


@pytest.mark.asyncio
async def test_provider_selects_source_update_then_fetch_time_per_hospital() -> None:
    """A newer fetch with unknown source time does not replace a known source update."""

    now = datetime(2026, 1, 1, 12, tzinfo=UTC)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        session.add_all(
            [
                _hospital("TEST_HOSPITAL_001", now),
                _hospital("TEST_HOSPITAL_002", now),
            ]
        )
        await session.flush()
        session.add_all(
            [
                _status(
                    "TEST_HOSPITAL_001",
                    "TEST_STATUS_OLDER",
                    now,
                    now + timedelta(minutes=1),
                ),
                _status(
                    "TEST_HOSPITAL_001",
                    "TEST_STATUS_UNKNOWN_TIME",
                    None,
                    now + timedelta(hours=1),
                ),
                _status(
                    "TEST_HOSPITAL_001",
                    "TEST_STATUS_LATEST_SOURCE",
                    now + timedelta(minutes=10),
                    now + timedelta(minutes=11),
                ),
                _status(
                    "TEST_HOSPITAL_001",
                    "TEST_STATUS_UNVERIFIED_TIMESTAMP",
                    now + timedelta(days=1),
                    now + timedelta(minutes=12),
                    source_timezone="unknown",
                ),
                _status(
                    "TEST_HOSPITAL_002",
                    "TEST_STATUS_SAME_TIME_OLDER_FETCH",
                    now,
                    now + timedelta(minutes=1),
                ),
                _status(
                    "TEST_HOSPITAL_002",
                    "TEST_STATUS_SAME_TIME_NEWER_FETCH",
                    now,
                    now + timedelta(minutes=2),
                ),
            ]
        )
        await session.commit()

        latest = await DatabaseRealtimeStatusProvider(session).load(
            ["TEST_HOSPITAL_001", "TEST_HOSPITAL_002"]
        )

        assert latest["TEST_HOSPITAL_001"]["source_record_id"] == (
            "TEST_STATUS_LATEST_SOURCE"
        )
        assert latest["TEST_HOSPITAL_002"]["source_record_id"] == (
            "TEST_STATUS_SAME_TIME_NEWER_FETCH"
        )

    await engine.dispose()
