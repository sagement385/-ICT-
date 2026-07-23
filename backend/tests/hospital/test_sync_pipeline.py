"""HIRA basic sync pipeline test with a TEST-only raw response."""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.database import Base
from app.integrations.common.base_client import RawExternalResponse
from app.modules.hospital.models import DataSourceRegistry, Hospital
from app.modules.patient.models import RawIngestionEvent
from app.pipelines.hospital_sync import pipeline

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "hira-basic-test.xml"


class FakeHiraClient:
    """Return one verified-shape TEST page without network access."""

    async def fetch_basic_page(
        self,
        page_no: int,
        num_of_rows: int,
        sido_code: str,
    ) -> RawExternalResponse:
        """Return the local fixture and verify configured pagination inputs."""

        assert page_no == 1
        assert num_of_rows == 1000
        assert sido_code == "TEST_REGION_CODE"
        return RawExternalResponse(
            request_id="TEST_REQUEST_ID",
            status_code=200,
            fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
            headers={},
            payload=FIXTURE_PATH.read_text(encoding="utf-8"),
        )


@pytest.mark.asyncio
async def test_pipeline_preserves_raw_and_normalized_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI pipeline has one ordered source of truth for raw and normalized rows."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(pipeline, "get_session_factory", lambda: session_factory)
    monkeypatch.setattr(
        pipeline,
        "get_settings",
        lambda: SimpleNamespace(
            chungbuk_sido_code="TEST_REGION_CODE",
            hira_base_url="https://example.invalid/hira",
        ),
    )

    loaded = await pipeline.sync_hospitals(client=FakeHiraClient())  # type: ignore[arg-type]

    async with session_factory() as session:
        hospital = await session.get(Hospital, "TEST_HOSPITAL_001_ID")
        registry = await session.scalar(
            select(DataSourceRegistry).where(
                DataSourceRegistry.source_name == "hira-hospital-info"
            )
        )
        raw_count = await session.scalar(select(func.count()).select_from(RawIngestionEvent))

    assert loaded == 1
    assert hospital is not None
    assert hospital.raw_payload_id is not None
    assert hospital.hospital_name == "TEST_HOSPITAL_001"
    assert registry is not None
    assert registry.last_success_at is not None
    assert raw_count == 1
    await engine.dispose()
