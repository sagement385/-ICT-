"""Store raw NEMC realtime status and exact-name matches for HIRA hospitals."""

import asyncio
import logging
import re
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.integrations.nemc.client import NemcEmergencyClient
from app.integrations.nemc.parser import parse_realtime_records, parse_total_count
from app.modules.hospital.data_source_registry import (
    DataSourceRegistryRepository,
    safe_collection_error_code,
)
from app.modules.hospital.models import Hospital, HospitalRealtimeStatus
from app.modules.patient.models import RawIngestionEvent

logger = logging.getLogger(__name__)


async def sync_realtime_status() -> int:
    """Fetch realtime data and link only exact normalized-name matches."""

    settings = get_settings()
    client = NemcEmergencyClient()
    session_factory = get_session_factory()
    loaded = 0
    async with session_factory() as session:
        registry = DataSourceRegistryRepository(session)
        try:
            hospitals = list((await session.execute(select(Hospital))).scalars())
            by_name: dict[str, list[Hospital]] = {}
            for hospital in hospitals:
                by_name.setdefault(_normalize_name(hospital.hospital_name), []).append(hospital)
            page_no = 1
            num_of_rows = 1000
            total_count = 0
            unmatched = 0
            ambiguous = 0
            while page_no == 1 or page_no * num_of_rows < total_count:
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
                    matches = by_name.get(_normalize_name(record.institution_name or ""), [])
                    if not matches:
                        unmatched += 1
                        continue
                    if len(matches) != 1:
                        ambiguous += 1
                        continue
                    hospital = matches[0]
                    await session.merge(
                        HospitalRealtimeStatus(
                            id=_stable_status_id(record.source_record_id, page_no),
                            hospital_id=hospital.hospital_id,
                            acceptance_status=None,
                            available_beds=None,
                            source_name="nemc-emergency-medical",
                            source_record_id=record.source_record_id,
                            raw_payload_id=raw_event.id,
                            schema_version="nemc-realtime.raw.v1",
                            source_updated_at=record.source_updated_at,
                            fetched_at=response.fetched_at,
                        )
                    )
                    loaded += 1
                total_count = parse_total_count(response.payload)
                page_no += 1
            await registry.mark_success(
                source_name="nemc-emergency-medical",
                dataset_id=None,
                provider_name="National Emergency Medical Center",
                base_url=settings.nemc_base_url,
                auth_type="serviceKey query parameter",
                schema_version="nemc-realtime.raw.v1",
            )
            await session.commit()
            logger.info(
                "NEMC exact-name matching completed loaded=%s unmatched=%s ambiguous=%s",
                loaded,
                unmatched,
                ambiguous,
            )
        except Exception as error:
            await session.rollback()
            await registry.mark_failure(
                source_name="nemc-emergency-medical",
                dataset_id=None,
                provider_name="National Emergency Medical Center",
                base_url=settings.nemc_base_url,
                auth_type="serviceKey query parameter",
                schema_version="nemc-realtime.raw.v1",
                error_code=safe_collection_error_code(error),
            )
            await session.commit()
            raise
    return loaded


def _normalize_name(value: str) -> str:
    """Normalize spacing and punctuation for an exact-name cross-source match."""

    return re.sub(r"[^0-9\uac00-\ud7a3A-Za-z]", "", value).lower()


def _stable_status_id(source_record_id: str, page_no: int) -> str:
    """Build an idempotent row id without relying on provider identifier length."""

    return str(uuid5(NAMESPACE_URL, f"nemc:{source_record_id}:{page_no}"))


def main() -> None:
    """Run realtime status synchronization."""

    loaded = asyncio.run(sync_realtime_status())
    print(f"Loaded {loaded} exact-name realtime status matches.")


if __name__ == "__main__":
    main()
