"""Synchronize official NEMC emergency institutions and link them to HIRA hospitals."""

import asyncio
import logging
from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.errors import ApplicationError
from app.integrations.nemc.client import NemcEmergencyClient
from app.integrations.nemc.parser import parse_emergency_institutions, parse_total_count
from app.modules.hospital.data_source_registry import (
    DataSourceRegistryRepository,
    safe_collection_error_code,
)
from app.modules.hospital.models import Hospital, HospitalEmergencyProfile
from app.modules.hospital.source_linker import match_emergency_institution
from app.modules.patient.models import RawIngestionEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmergencyInstitutionSyncSummary:
    """Safe aggregate result without institution identifiers or personal data."""

    source_records: int
    region_records: int
    linked: int
    unmatched: int
    ambiguous: int
    coordinate_warnings: int


async def sync_emergency_institutions() -> EmergencyInstitutionSyncSummary:
    """Store raw list pages and upsert only unambiguous Chungbuk profile links."""

    settings = get_settings()
    client = NemcEmergencyClient()
    session_factory = get_session_factory()
    source_records = 0
    region_records = 0
    linked = 0
    unmatched = 0
    ambiguous = 0
    coordinate_warnings = 0
    linked_source_ids: set[str] = set()
    async with session_factory() as session:
        registry = DataSourceRegistryRepository(session)
        try:
            hospitals = list((await session.execute(select(Hospital))).scalars())
            if not hospitals:
                raise ApplicationError(
                    code="HOSPITAL_DATA_REQUIRED",
                    message="NEMC 기관을 연결할 HIRA 병원 데이터가 없습니다.",
                    details={"required_command": "python scripts/sync_hospital_data.py"},
                )

            page_no = 1
            page_size = 1000
            total_count = 0
            while page_no == 1 or (page_no - 1) * page_size < total_count:
                response = await client.fetch_emergency_institutions(page_no, page_size)
                records = parse_emergency_institutions(response.payload)
                total_count = parse_total_count(response.payload)
                source_records += len(records)
                raw_event = RawIngestionEvent(
                    source_name="nemc-emergency-institution-list",
                    source_record_id=f"page-{page_no}",
                    payload_json={"raw_payload": response.payload},
                    schema_version="nemc-emergency-list.raw.v1",
                    fetched_at=response.fetched_at,
                )
                session.add(raw_event)
                await session.flush()

                for record in records:
                    if not (record.address or "").startswith(settings.chungbuk_region_name):
                        continue
                    region_records += 1
                    match = match_emergency_institution(
                        record,
                        hospitals,
                        settings.nemc_hira_coordinate_warning_meters,
                    )
                    if match.status == "unmatched":
                        unmatched += 1
                        continue
                    if match.status == "ambiguous" or match.hospital is None:
                        ambiguous += 1
                        continue
                    coordinate_warnings += int(match.coordinate_warning)
                    await session.merge(
                        HospitalEmergencyProfile(
                            id=_stable_profile_id(record.source_record_id),
                            hospital_id=match.hospital.hospital_id,
                            source_name="nemc-emergency-institution-list",
                            source_record_id=record.source_record_id,
                            source_institution_name=record.institution_name,
                            source_address=record.address,
                            source_latitude=record.latitude,
                            source_longitude=record.longitude,
                            emergency_type_code=record.emergency_type_code,
                            emergency_type_name=record.emergency_type_name,
                            representative_phone=record.representative_phone,
                            emergency_phone=record.emergency_phone,
                            match_method="exact_normalized_name_unique",
                            active=True,
                            coordinate_distance_meters=match.coordinate_distance_meters,
                            coordinate_warning=match.coordinate_warning,
                            raw_payload_id=raw_event.id,
                            schema_version="nemc-emergency-list.v1",
                            source_updated_at=None,
                            fetched_at=response.fetched_at,
                        )
                    )
                    linked += 1
                    linked_source_ids.add(record.source_record_id)
                page_no += 1

            if region_records == 0:
                raise ApplicationError(
                    code="NEMC_REGION_DATA_EMPTY",
                    message="NEMC 응급의료기관 목록에 설정된 지역 데이터가 없습니다.",
                    details={"region_setting": "CHUNGBUK_REGION_NAME"},
                )
            existing_profiles = list(
                (
                    await session.execute(
                        select(HospitalEmergencyProfile).where(
                            HospitalEmergencyProfile.source_name
                            == "nemc-emergency-institution-list"
                        )
                    )
                ).scalars()
            )
            for profile in existing_profiles:
                profile.active = profile.source_record_id in linked_source_ids
            await registry.mark_success(
                source_name="nemc-emergency-institution-list",
                dataset_id="15000563",
                provider_name="National Emergency Medical Center",
                base_url=settings.nemc_base_url,
                auth_type="serviceKey query parameter",
                schema_version="nemc-emergency-list.v1",
            )
            await session.commit()
        except Exception as error:
            await session.rollback()
            await registry.mark_failure(
                source_name="nemc-emergency-institution-list",
                dataset_id="15000563",
                provider_name="National Emergency Medical Center",
                base_url=settings.nemc_base_url,
                auth_type="serviceKey query parameter",
                schema_version="nemc-emergency-list.v1",
                error_code=safe_collection_error_code(error),
            )
            await session.commit()
            raise

    summary = EmergencyInstitutionSyncSummary(
        source_records=source_records,
        region_records=region_records,
        linked=linked,
        unmatched=unmatched,
        ambiguous=ambiguous,
        coordinate_warnings=coordinate_warnings,
    )
    logger.info("NEMC emergency institution sync completed summary=%s", summary)
    return summary


def _stable_profile_id(source_record_id: str) -> str:
    """Build an idempotent profile ID from the provider record identifier."""

    return str(uuid5(NAMESPACE_URL, f"nemc-emergency-profile:{source_record_id}"))


def main() -> None:
    """Run the source-backed emergency-institution synchronization."""

    summary = asyncio.run(sync_emergency_institutions())
    print(
        "NEMC emergency institution sync: "
        f"source={summary.source_records}, region={summary.region_records}, "
        f"linked={summary.linked}, unmatched={summary.unmatched}, "
        f"ambiguous={summary.ambiguous}, coordinate_warnings={summary.coordinate_warnings}"
    )


if __name__ == "__main__":
    main()
