"""Synchronize verified HIRA hospital detail rows after basic data is loaded."""

import argparse
import asyncio
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from app.core.database import get_session_factory
from app.integrations.hira.client import HiraClient
from app.integrations.hira.detail_parser import parse_detail
from app.modules.hospital.models import Hospital, HospitalCapability, HospitalDepartment
from app.modules.patient.models import RawIngestionEvent


async def sync_hospital_details(
    endpoint: str | None = None,
    hospital_id: str | None = None,
    limit: int | None = None,
) -> int:
    """Fetch verified detail endpoints and upsert only confirmed normalized rows."""

    if limit is not None and limit < 1:
        raise ValueError("limit must be greater than zero")

    client = HiraClient()
    endpoints = (endpoint,) if endpoint else client.detail_endpoints
    session_factory = get_session_factory()
    loaded = 0
    async with session_factory() as session:
        statement = select(Hospital).order_by(Hospital.hospital_id)
        if hospital_id is not None:
            statement = statement.where(Hospital.hospital_id == hospital_id)
        if limit is not None:
            statement = statement.limit(limit)
        hospitals = list((await session.execute(statement)).scalars())
        for hospital in hospitals:
            for detail_endpoint in endpoints:
                response = await client.fetch_detail(detail_endpoint, hospital.hospital_id)
                parsed = parse_detail(detail_endpoint, response.payload)
                raw_event = RawIngestionEvent(
                    source_name="hira-hospital-detail",
                    source_record_id=f"{hospital.hospital_id}:{detail_endpoint}",
                    payload_json={"raw_payload": response.payload},
                    schema_version="hira-hospital-detail.raw.v1",
                    fetched_at=response.fetched_at,
                )
                session.add(raw_event)
                await session.flush()
                for index, department in enumerate(parsed.departments):
                    await session.merge(
                        HospitalDepartment(
                            id=_stable_id(hospital.hospital_id, detail_endpoint, department.department_code, index),
                            hospital_id=hospital.hospital_id,
                            department_code=department.department_code,
                            department_name=department.department_name,
                            specialist_count=department.specialist_count,
                            source_updated_at=None,
                        )
                    )
                    loaded += 1
                for index, capability in enumerate(parsed.capabilities):
                    await session.merge(
                        HospitalCapability(
                            id=_stable_id(hospital.hospital_id, detail_endpoint, capability.capability_code, index),
                            hospital_id=hospital.hospital_id,
                            capability_code=capability.capability_code,
                            capability_name=capability.capability_name,
                            available=capability.available,
                            source_updated_at=None,
                        )
                    )
                    loaded += 1
            await session.commit()
    return loaded


def _stable_id(hospital_id: str, endpoint: str, code: str, index: int) -> str:
    """Create an idempotent child-row identifier without a hardcoded operational value."""

    return str(uuid5(NAMESPACE_URL, f"hira:{hospital_id}:{endpoint}:{code}:{index}"))


def main() -> None:
    """Run the detail synchronization command."""

    parser = argparse.ArgumentParser(description="Sync verified HIRA hospital detail data")
    parser.add_argument("--endpoint", choices=HiraClient.detail_endpoints)
    parser.add_argument("--hospital-id", help="Synchronize one already-loaded HIRA hospital")
    parser.add_argument("--limit", type=int, help="Maximum number of already-loaded hospitals to process")
    args = parser.parse_args()
    loaded = asyncio.run(
        sync_hospital_details(
            endpoint=args.endpoint,
            hospital_id=args.hospital_id,
            limit=args.limit,
        )
    )
    print(f"Loaded {loaded} normalized HIRA detail rows.")


if __name__ == "__main__":
    main()
