"""Tests for official emergency-institution eligibility filtering."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.errors import ApplicationError
from app.integrations.nemc.schemas import NemcEmergencyInstitutionRecord
from app.modules.hospital.models import Hospital, HospitalEmergencyProfile
from app.modules.hospital.repository import HospitalRepository
from app.modules.hospital.service import HospitalService
from app.modules.hospital.source_linker import match_emergency_institution


def test_source_linker_requires_one_exact_normalized_name() -> None:
    """Fuzzy or ambiguous names never become emergency eligibility links."""

    record = NemcEmergencyInstitutionRecord(
        source_record_id="TEST_NEMC_001",
        institution_name="TEST HOSPITAL 001",
        address="TEST_REGION TEST_ADDRESS",
        emergency_type_code="TEST_TYPE",
        emergency_type_name="TEST_TYPE_NAME",
        representative_phone=None,
        emergency_phone=None,
        latitude=0.0,
        longitude=0.0,
        raw_fields={},
    )
    hospital = Hospital(
        hospital_id="TEST_HOSPITAL_001",
        hospital_name="TEST-HOSPITAL-001",
        latitude=0.0,
        longitude=0.0,
        source_name="TEST_HIRA",
        schema_version="test.v1",
    )

    match = match_emergency_institution(record, [hospital], 1000)

    assert match.status == "matched"
    assert match.hospital is hospital
    assert match.coordinate_warning is False


@pytest.mark.asyncio
async def test_nearby_query_excludes_hospitals_without_emergency_profile() -> None:
    """Distance alone cannot make a general HIRA institution a map candidate."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime(2026, 1, 1, tzinfo=UTC)

    async with session_factory() as session:
        eligible = Hospital(
            hospital_id="TEST_HOSPITAL_ELIGIBLE",
            hospital_name="TEST_HOSPITAL_ELIGIBLE",
            latitude=0.01,
            longitude=0.0,
            source_name="TEST_HIRA",
            schema_version="test-hira.v1",
        )
        ineligible = Hospital(
            hospital_id="TEST_HOSPITAL_INELIGIBLE",
            hospital_name="TEST_HOSPITAL_INELIGIBLE",
            latitude=0.02,
            longitude=0.0,
            source_name="TEST_HIRA",
            schema_version="test-hira.v1",
        )
        session.add_all([eligible, ineligible])
        session.add(
            HospitalEmergencyProfile(
                hospital_id=eligible.hospital_id,
                source_name="TEST_NEMC",
                source_record_id="TEST_NEMC_HPID_001",
                source_institution_name=eligible.hospital_name,
                source_address="TEST_ADDRESS",
                source_latitude=eligible.latitude,
                source_longitude=eligible.longitude,
                emergency_type_code="TEST_TYPE",
                emergency_type_name="TEST_TYPE_NAME",
                representative_phone=None,
                emergency_phone=None,
                match_method="TEST_MATCH",
                active=True,
                coordinate_distance_meters=0,
                coordinate_warning=False,
                raw_payload_id=None,
                schema_version="test-nemc.v1",
                source_updated_at=now,
                fetched_at=now,
            )
        )
        await session.commit()

        nearby = await HospitalRepository(session).list_nearby(0.0, 0.0, 10.0)
        response = await HospitalService(session).list_nearby(0.0, 0.0, 10.0)

        assert [item.hospital_id for item in nearby] == ["TEST_HOSPITAL_ELIGIBLE"]
        assert [item.hospital_id for item in response] == ["TEST_HOSPITAL_ELIGIBLE"]
        assert response[0].emergency_profile is not None

    await engine.dispose()


@pytest.mark.asyncio
async def test_nearby_query_fails_closed_before_emergency_sync() -> None:
    """An empty profile table returns a configuration error instead of all HIRA rows."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        with pytest.raises(ApplicationError) as error:
            await HospitalService(session).list_nearby(0.0, 0.0, 10.0)
        assert error.value.code == "EMERGENCY_INSTITUTION_DATA_NOT_SYNCED"

    await engine.dispose()
