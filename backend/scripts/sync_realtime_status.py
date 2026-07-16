"""Store raw NEMC realtime status through verified emergency profile links."""

import asyncio
import logging
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.errors import ApplicationError
from app.integrations.nemc.client import NemcEmergencyClient
from app.integrations.nemc.parser import parse_realtime_records, parse_total_count
from app.modules.hospital.data_source_registry import (
    DataSourceRegistryRepository,
    safe_collection_error_code,
)
from app.modules.hospital.models import (
    HospitalEmergencyProfile,
    HospitalRealtimeStatus,
)
from app.modules.patient.models import RawIngestionEvent

logger = logging.getLogger(__name__)


async def sync_realtime_status() -> int:
    """Fetch realtime data and link it through previously synchronized NEMC hpid profiles."""

    settings = get_settings()
    client = NemcEmergencyClient()
    session_factory = get_session_factory()
    loaded = 0
    async with session_factory() as session:
        registry = DataSourceRegistryRepository(session)
        try:
            profiles = list(
                (
                    await session.execute(
                        select(HospitalEmergencyProfile).where(
                            HospitalEmergencyProfile.source_name
                            == "nemc-emergency-institution-list",
                            HospitalEmergencyProfile.active.is_(True),
                        )
                    )
                ).scalars()
            )
            if not profiles:
                raise ApplicationError(
                    code="EMERGENCY_INSTITUTION_DATA_NOT_SYNCED",
                    message="응급의료기관 목록을 먼저 동기화해야 합니다.",
                    details={"required_command": "python scripts/sync_emergency_institutions.py"},
                )
            profile_by_source_id = {profile.source_record_id: profile for profile in profiles}
            existing_status_rows = list(
                (
                    await session.execute(
                        select(HospitalRealtimeStatus).where(
                            HospitalRealtimeStatus.source_name == "nemc-emergency-medical"
                        )
                    )
                ).scalars()
            )
            existing_by_source_id = {
                row.source_record_id: row
                for row in existing_status_rows
                if row.source_record_id is not None
            }
            page_no = 1
            num_of_rows = 100
            total_count = 0
            unmatched = 0
            while page_no == 1 or (page_no - 1) * num_of_rows < total_count:
                response = await client.fetch_realtime_status(
                    page_no=page_no,
                    num_of_rows=num_of_rows,
                )
                records = parse_realtime_records(response.payload)
                raw_event = RawIngestionEvent(
                    source_name="nemc-emergency-medical",
                    source_record_id=f"realtime-status-page-{page_no}",
                    payload_json={"raw_payload": response.payload},
                    schema_version="nemc-realtime.raw.v1",
                    fetched_at=response.fetched_at,
                )
                session.add(raw_event)
                await session.flush()
                for record in records:
                    profile = profile_by_source_id.get(record.source_record_id)
                    if profile is None:
                        unmatched += 1
                        continue
                    status = existing_by_source_id.get(record.source_record_id)
                    if status is None:
                        status = HospitalRealtimeStatus(
                            id=_stable_status_id(record.source_record_id, page_no),
                            source_name="nemc-emergency-medical",
                            source_record_id=record.source_record_id,
                        )
                        session.add(status)
                        existing_by_source_id[record.source_record_id] = status
                    status.hospital_id = profile.hospital_id
                    status.acceptance_status = None
                    status.available_beds = None
                    status.raw_payload_id = raw_event.id
                    status.schema_version = "nemc-realtime.raw.v1"
                    status.source_updated_at = record.source_updated_at
                    status.fetched_at = response.fetched_at
                    loaded += 1
                total_count = parse_total_count(response.payload)
                page_no += 1
            await registry.mark_success(
                source_name="nemc-emergency-medical",
                dataset_id="15000563",
                provider_name="National Emergency Medical Center",
                base_url=settings.nemc_base_url,
                auth_type="serviceKey query parameter",
                schema_version="nemc-realtime.raw.v1",
            )
            await session.commit()
            logger.info(
                "NEMC hpid profile matching completed loaded=%s unmatched=%s",
                loaded,
                unmatched,
            )
        except Exception as error:
            await session.rollback()
            await registry.mark_failure(
                source_name="nemc-emergency-medical",
                dataset_id="15000563",
                provider_name="National Emergency Medical Center",
                base_url=settings.nemc_base_url,
                auth_type="serviceKey query parameter",
                schema_version="nemc-realtime.raw.v1",
                error_code=safe_collection_error_code(error),
            )
            await session.commit()
            raise
    return loaded


def _stable_status_id(source_record_id: str, page_no: int) -> str:
    """Build an idempotent row id without relying on provider identifier length."""

    return str(uuid5(NAMESPACE_URL, f"nemc:{source_record_id}:{page_no}"))


def main() -> None:
    """Run realtime status synchronization."""

    loaded = asyncio.run(sync_realtime_status())
    print(f"Loaded {loaded} hpid-linked realtime status records.")


if __name__ == "__main__":
    main()
