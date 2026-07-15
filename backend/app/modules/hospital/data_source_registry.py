"""Persistence helpers for external data-source collection status."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hospital.models import DataSourceRegistry


class DataSourceRegistryRepository:
    """Update collection metadata without storing credentials or raw payloads."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def mark_success(
        self,
        *,
        source_name: str,
        dataset_id: str | None,
        provider_name: str,
        base_url: str | None,
        auth_type: str | None,
        schema_version: str,
        occurred_at: datetime | None = None,
    ) -> DataSourceRegistry:
        """Record a completed collection after its normalized writes succeed."""

        row = await self._get_or_create(
            source_name=source_name,
            dataset_id=dataset_id,
            provider_name=provider_name,
            base_url=base_url,
            auth_type=auth_type,
            schema_version=schema_version,
        )
        row.enabled = True
        row.last_success_at = occurred_at or datetime.now(UTC)
        row.last_error = None
        await self.session.flush()
        return row

    async def mark_failure(
        self,
        *,
        source_name: str,
        dataset_id: str | None,
        provider_name: str,
        base_url: str | None,
        auth_type: str | None,
        schema_version: str,
        error_code: str,
        occurred_at: datetime | None = None,
    ) -> DataSourceRegistry:
        """Record only a safe error code, never an exception payload or API key."""

        row = await self._get_or_create(
            source_name=source_name,
            dataset_id=dataset_id,
            provider_name=provider_name,
            base_url=base_url,
            auth_type=auth_type,
            schema_version=schema_version,
        )
        row.enabled = True
        row.last_failure_at = occurred_at or datetime.now(UTC)
        row.last_error = error_code
        await self.session.flush()
        return row

    async def _get_or_create(
        self,
        *,
        source_name: str,
        dataset_id: str | None,
        provider_name: str,
        base_url: str | None,
        auth_type: str | None,
        schema_version: str,
    ) -> DataSourceRegistry:
        """Find one source by stable name or create its non-secret metadata row."""

        row = (
            await self.session.execute(
                select(DataSourceRegistry).where(DataSourceRegistry.source_name == source_name)
            )
        ).scalars().first()
        if row is None:
            row = DataSourceRegistry(
                source_name=source_name,
                dataset_id=dataset_id,
                provider_name=provider_name,
                base_url=base_url,
                auth_type=auth_type,
                enabled=True,
                schema_version=schema_version,
            )
            self.session.add(row)
        else:
            row.dataset_id = dataset_id
            row.provider_name = provider_name
            row.base_url = base_url
            row.auth_type = auth_type
            row.schema_version = schema_version
        return row


def safe_collection_error_code(error: Exception) -> str:
    """Reduce an exception to a non-sensitive registry value."""

    code = getattr(error, "code", None)
    return str(code) if isinstance(code, str) else type(error).__name__
