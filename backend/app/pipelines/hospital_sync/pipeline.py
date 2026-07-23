"""Transactional HIRA basic-data synchronization pipeline."""

import httpx

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.integrations.hira.client import HiraClient
from app.integrations.hira.parser import parse_total_count
from app.modules.hospital.data_source_registry import (
    DataSourceRegistryRepository,
    safe_collection_error_code,
)
from app.pipelines.hospital_sync.fetch import fetch
from app.pipelines.hospital_sync.load import load
from app.pipelines.hospital_sync.normalize import normalize
from app.pipelines.hospital_sync.save_raw import save_raw
from app.pipelines.hospital_sync.validate import validate

SOURCE_NAME = "hira-hospital-info"
RAW_SCHEMA_VERSION = "hira-hospital-info.raw.v1"
NORMALIZED_SCHEMA_VERSION = "hira-hospital-info.v1"


async def sync_hospitals(
    limit: int | None = None,
    page_size: int = 1000,
    *,
    client: HiraClient | None = None,
) -> int:
    """Run fetch, raw storage, normalization, validation, and loading in order."""

    if limit is not None and limit < 1:
        raise ValueError("limit must be greater than zero")
    if not 1 <= page_size <= 1000:
        raise ValueError("page_size must be between 1 and 1000")

    if client is not None:
        return await _sync_with_client(client, limit, page_size)
    async with httpx.AsyncClient() as http_client:
        return await _sync_with_client(
            HiraClient(http_client=http_client),
            limit,
            page_size,
        )


async def _sync_with_client(
    client: HiraClient,
    limit: int | None,
    page_size: int,
) -> int:
    """Execute the transactional pipeline using an injected HTTP boundary."""

    settings = get_settings()
    session_factory = get_session_factory()
    loaded = 0
    page_no = 1
    async with session_factory() as session:
        registry = DataSourceRegistryRepository(session)
        try:
            while True:
                response = await fetch(
                    client,
                    page_no,
                    page_size,
                    settings.chungbuk_sido_code,
                )
                raw_payload_id = await save_raw(
                    session,
                    response,
                    SOURCE_NAME,
                    f"page-{page_no}",
                    RAW_SCHEMA_VERSION,
                )
                records = normalize(response.payload, response.fetched_at)
                if not records:
                    break
                if limit is not None:
                    records = records[: max(limit - loaded, 0)]

                for record in records:
                    await load(session, validate(record), raw_payload_id)
                    loaded += 1

                if limit is not None and loaded >= limit:
                    break
                total_count = parse_total_count(response.payload)
                if page_no * page_size >= total_count:
                    break
                page_no += 1

            await registry.mark_success(
                source_name=SOURCE_NAME,
                dataset_id="15001698",
                provider_name="Health Insurance Review & Assessment Service",
                base_url=settings.hira_base_url,
                auth_type="serviceKey query parameter",
                schema_version=NORMALIZED_SCHEMA_VERSION,
            )
            await session.commit()
        except Exception as error:
            await session.rollback()
            await registry.mark_failure(
                source_name=SOURCE_NAME,
                dataset_id="15001698",
                provider_name="Health Insurance Review & Assessment Service",
                base_url=settings.hira_base_url,
                auth_type="serviceKey query parameter",
                schema_version=NORMALIZED_SCHEMA_VERSION,
                error_code=safe_collection_error_code(error),
            )
            await session.commit()
            raise
    return loaded
