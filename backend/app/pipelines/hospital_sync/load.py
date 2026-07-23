"""Hospital normalized loading stage."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.hira.parser import HiraBasicHospital
from app.modules.hospital.models import Hospital


async def load(
    session: AsyncSession,
    record: HiraBasicHospital,
    raw_payload_id: str,
) -> None:
    """Upsert one normalized HIRA basic record into the hospital table."""

    await session.merge(
        Hospital(
            hospital_id=record.hospital_id,
            hospital_name=record.hospital_name,
            hospital_type_code=record.hospital_type_code,
            address=record.address,
            latitude=record.latitude,
            longitude=record.longitude,
            phone=record.phone,
            source_name="hira-hospital-info",
            source_record_id=record.hospital_id,
            raw_payload_id=raw_payload_id,
            schema_version="hira-hospital-info.v1",
            source_updated_at=record.source_updated_at,
        )
    )
