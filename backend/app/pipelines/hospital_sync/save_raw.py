"""Raw response storage stage."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.common.base_client import RawExternalResponse
from app.modules.patient.models import RawIngestionEvent


async def save_raw(
    session: AsyncSession,
    response: RawExternalResponse,
    source_name: str,
    source_record_id: str,
    schema_version: str,
) -> str:
    """Persist a raw payload and return its generated id."""

    event = RawIngestionEvent(
        source_name=source_name,
        source_record_id=source_record_id,
        payload_json={"raw_payload": response.payload},
        schema_version=schema_version,
        fetched_at=response.fetched_at,
    )
    session.add(event)
    await session.flush()
    return event.id
