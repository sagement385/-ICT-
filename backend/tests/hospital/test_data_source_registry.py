"""Data-source registry tests with isolated TEST metadata."""

import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.modules.hospital.data_source_registry import DataSourceRegistryRepository

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "recommendation-policy-engine-test.json"


@pytest.mark.asyncio
async def test_registry_retains_failure_time_and_clears_error_after_success() -> None:
    """Collection status changes without storing credentials or response payloads."""

    fixture: dict[str, Any] = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    data = fixture["registry"]
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        repository = DataSourceRegistryRepository(session)
        failed = await repository.mark_failure(
            source_name=data["source_name"],
            dataset_id=data["dataset_id"],
            provider_name=data["provider_name"],
            base_url=data["base_url"],
            auth_type=data["auth_type"],
            schema_version=data["schema_version"],
            error_code=data["error_code"],
        )
        await session.commit()
        assert failed.last_error == data["error_code"]
        assert failed.last_failure_at is not None

        succeeded = await repository.mark_success(
            source_name=data["source_name"],
            dataset_id=data["dataset_id"],
            provider_name=data["provider_name"],
            base_url=data["base_url"],
            auth_type=data["auth_type"],
            schema_version=data["schema_version"],
        )
        await session.commit()
        assert succeeded.id == failed.id
        assert succeeded.last_success_at is not None
        assert succeeded.last_error is None

    await engine.dispose()
