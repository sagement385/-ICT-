"""Synchronize verified HIRA hospital detail rows after basic data is loaded."""

import argparse
import asyncio
from uuid import NAMESPACE_URL, uuid5

import httpx
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.integrations.hira.client import HiraClient
from app.integrations.hira.detail_parser import parse_detail
from app.modules.hospital.data_source_registry import (
    DataSourceRegistryRepository,
    safe_collection_error_code,
)
from app.modules.hospital.models import (
    Hospital,
    HospitalCapability,
    HospitalDepartment,
    HospitalEmergencyProfile,
    HospitalEquipment,
)
from app.modules.patient.models import RawIngestionEvent


async def sync_hospital_details(
    endpoint: str | None = None,
    hospital_id: str | None = None,
    limit: int | None = None,
    emergency_only: bool = False,
    normalized_only: bool = False,
) -> int:
    """Fetch verified detail endpoints and upsert only confirmed normalized rows."""

    if limit is not None and limit < 1:
        raise ValueError("limit must be greater than zero")

    http_client = httpx.AsyncClient(timeout=30.0)
    client = HiraClient(http_client=http_client)
    settings = get_settings()
    endpoints = (
        (endpoint,)
        if endpoint
        else (
            client.normalized_detail_endpoints
            if normalized_only
            else client.detail_endpoints
        )
    )
    session_factory = get_session_factory()
    loaded = 0
    async with session_factory() as session:
        registry = DataSourceRegistryRepository(session)
        try:
            statement = select(Hospital).order_by(Hospital.hospital_id)
            if emergency_only:
                statement = (
                    statement.join(
                        HospitalEmergencyProfile,
                        HospitalEmergencyProfile.hospital_id == Hospital.hospital_id,
                    )
                    .where(HospitalEmergencyProfile.active.is_(True))
                    .distinct()
                )
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
                                id=_stable_id(
                                    hospital.hospital_id,
                                    detail_endpoint,
                                    department.department_code,
                                    index,
                                ),
                                hospital_id=hospital.hospital_id,
                                department_code=department.department_code,
                                department_name=department.department_name,
                                specialist_count=department.specialist_count,
                                source_name="hira-hospital-detail",
                                source_record_id=(
                                    f"{hospital.hospital_id}:{detail_endpoint}:"
                                    f"{department.department_code}:{index}"
                                ),
                                raw_payload_id=raw_event.id,
                                schema_version="hira-hospital-detail.v1",
                                fetched_at=response.fetched_at,
                                source_updated_at=None,
                            )
                        )
                        loaded += 1
                    for index, capability in enumerate(parsed.capabilities):
                        await session.merge(
                            HospitalCapability(
                                id=_stable_id(
                                    hospital.hospital_id,
                                    detail_endpoint,
                                    capability.capability_code,
                                    index,
                                ),
                                hospital_id=hospital.hospital_id,
                                capability_code=capability.capability_code,
                                capability_name=capability.capability_name,
                                available=capability.available,
                                source_name="hira-hospital-detail",
                                source_record_id=(
                                    f"{hospital.hospital_id}:{detail_endpoint}:"
                                    f"{capability.capability_code}:{index}"
                                ),
                                raw_payload_id=raw_event.id,
                                schema_version="hira-hospital-detail.v1",
                                fetched_at=response.fetched_at,
                                source_updated_at=None,
                            )
                        )
                        loaded += 1
                    for index, equipment in enumerate(parsed.equipment):
                        await session.merge(
                            HospitalEquipment(
                                id=_stable_id(
                                    hospital.hospital_id,
                                    detail_endpoint,
                                    equipment.equipment_code,
                                    index,
                                ),
                                hospital_id=hospital.hospital_id,
                                equipment_code=equipment.equipment_code,
                                equipment_name=equipment.equipment_name,
                                equipment_count=equipment.equipment_count,
                                source_name="hira-hospital-detail",
                                source_record_id=(
                                    f"{hospital.hospital_id}:{detail_endpoint}:"
                                    f"{equipment.equipment_code}:{index}"
                                ),
                                raw_payload_id=raw_event.id,
                                schema_version="hira-hospital-detail.v1",
                                fetched_at=response.fetched_at,
                                source_updated_at=None,
                            )
                        )
                        loaded += 1
                await session.commit()
            await registry.mark_success(
                source_name="hira-hospital-detail",
                dataset_id="15001699",
                provider_name="Health Insurance Review & Assessment Service",
                base_url=settings.hira_detail_base_url,
                auth_type="serviceKey query parameter",
                schema_version="hira-hospital-detail.v1",
            )
            await session.commit()
        except Exception as error:
            await session.rollback()
            await registry.mark_failure(
                source_name="hira-hospital-detail",
                dataset_id="15001699",
                provider_name="Health Insurance Review & Assessment Service",
                base_url=settings.hira_detail_base_url,
                auth_type="serviceKey query parameter",
                schema_version="hira-hospital-detail.v1",
                error_code=safe_collection_error_code(error),
            )
            await session.commit()
            await http_client.aclose()
            raise
    await http_client.aclose()
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
    parser.add_argument(
        "--emergency-only",
        action="store_true",
        help="Process only hospitals linked to active official emergency institutions",
    )
    parser.add_argument(
        "--normalized-only",
        action="store_true",
        help="Call only endpoints with verified normalized field mappings",
    )
    args = parser.parse_args()
    loaded = asyncio.run(
        sync_hospital_details(
            endpoint=args.endpoint,
            hospital_id=args.hospital_id,
            limit=args.limit,
            emergency_only=args.emergency_only,
            normalized_only=args.normalized_only,
        )
    )
    print(f"Loaded {loaded} normalized HIRA detail rows.")


if __name__ == "__main__":
    main()
