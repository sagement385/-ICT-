"""Raw response storage stage."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.patient.models import RawIngestionEvent


async def save_raw(session: AsyncSession, response: dict[str, object], source_name: str, schema_version: str) -> str:
    """Persist a raw payload and return its generated id."""

    event = RawIngestionEvent(
        source_name=source_name,
        source_record_id=None,
        payload_json=response,
        schema_version=schema_version,
        fetched_at=datetime.now(UTC),
    )
    session.add(event)
    await session.flush()
    return event.id
