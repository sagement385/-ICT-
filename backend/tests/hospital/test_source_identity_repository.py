"""Cross-source identity tests with explicit human-verification boundaries."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.modules.hospital.models import Hospital
from app.modules.hospital.source_identity_repository import (
    HospitalSourceIdentityRepository,
)


@pytest.mark.asyncio
async def test_automated_identity_stays_unverified_until_explicit_review() -> None:
    """Automated candidates cannot become verified or overwrite a reviewed mapping."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        session.add(
            Hospital(
                hospital_id="TEST_HOSPITAL_001",
                hospital_name="TEST_HOSPITAL_NAME",
                hospital_type_code=None,
                address=None,
                latitude=None,
                longitude=None,
                phone=None,
                source_name="TEST_HIRA",
                source_record_id="TEST_YKIHO_001",
                raw_payload_id=None,
                schema_version="test.v1",
                source_updated_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        await session.flush()
        repository = HospitalSourceIdentityRepository(session)
        candidate = await repository.record_candidate(
            hospital_id="TEST_HOSPITAL_001",
            source_name="TEST_NEMC",
            source_record_id="TEST_HPID_001",
            source_hospital_name="TEST_HOSPITAL_NAME",
            match_method="exact_normalized_name_unique",
            match_confidence=None,
        )
        assert candidate.verified is False
        assert await repository.get_verified("TEST_NEMC", "TEST_HPID_001") is None

        verified = await repository.verify(
            source_name="TEST_NEMC",
            source_record_id="TEST_HPID_001",
            hospital_id="TEST_HOSPITAL_001",
        )
        assert verified is not None
        assert verified.verified is True

        unchanged = await repository.record_candidate(
            hospital_id="TEST_HOSPITAL_001",
            source_name="TEST_NEMC",
            source_record_id="TEST_HPID_001",
            source_hospital_name="TEST_AUTOMATED_RETRY_NAME",
            match_method="automated_retry",
            match_confidence=0.5,
        )
        assert unchanged.verified is True
        assert unchanged.source_hospital_name == "TEST_HOSPITAL_NAME"
        assert unchanged.match_method == "exact_normalized_name_unique"

    await engine.dispose()
