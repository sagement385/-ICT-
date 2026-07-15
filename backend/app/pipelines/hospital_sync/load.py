"""Hospital normalized loading stage."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hospital.models import Hospital


async def load(session: AsyncSession, record: dict[str, Any]) -> None:
    """Upsert one normalized HIRA basic record into the hospital table."""

    await session.merge(
        Hospital(
            hospital_id=str(record["hospital_id"]),
            hospital_name=str(record["hospital_name"]),
            hospital_type_code=record.get("hospital_type_code"),
            address=record.get("address"),
            latitude=record.get("latitude"),
            longitude=record.get("longitude"),
            phone=record.get("phone"),
            source_name="hira-hospital-info",
            source_record_id=str(record["hospital_id"]),
            raw_payload_id=record.get("raw_payload_id"),
            schema_version="hira-hospital-info.v1",
            source_updated_at=record.get("source_updated_at"),
        )
    )
