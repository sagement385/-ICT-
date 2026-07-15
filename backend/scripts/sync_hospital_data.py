"""Synchronize Chungbuk HIRA basic hospital records after API configuration."""

import argparse
import asyncio

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.integrations.hira.client import HiraClient
from app.integrations.hira.parser import parse_basic_hospitals, parse_total_count
from app.modules.hospital.models import Hospital
from app.modules.patient.models import RawIngestionEvent


async def sync_hospitals(limit: int | None = None, page_size: int = 1000) -> int:
    """Fetch all configured-region basic records and upsert source-backed rows."""

    if limit is not None and limit < 1:
        raise ValueError("limit must be greater than zero")
    if not 1 <= page_size <= 1000:
        raise ValueError("page_size must be between 1 and 1000")

    settings = get_settings()
    client = HiraClient()
    session_factory = get_session_factory()
    page_no = 1
    loaded = 0
    async with session_factory() as session:
        while True:
            response = await client.fetch_basic_page(page_no, page_size, settings.chungbuk_sido_code)
            payload = response.payload
            page_hospitals = parse_basic_hospitals(payload, response.fetched_at)
            if not page_hospitals:
                break
            hospitals = page_hospitals
            if limit is not None:
                hospitals = page_hospitals[: max(limit - loaded, 0)]
            raw_event = RawIngestionEvent(
                source_name="hira-hospital-info",
                source_record_id=f"page-{page_no}",
                payload_json={"raw_payload": payload},
                schema_version="hira-hospital-info.raw.v1",
                fetched_at=response.fetched_at,
            )
            session.add(raw_event)
            await session.flush()
            for item in hospitals:
                await session.merge(
                    Hospital(
                        hospital_id=item.hospital_id,
                        hospital_name=item.hospital_name,
                        hospital_type_code=item.hospital_type_code,
                        address=item.address,
                        latitude=item.latitude,
                        longitude=item.longitude,
                        phone=item.phone,
                        source_name="hira-hospital-info",
                        source_record_id=item.hospital_id,
                        raw_payload_id=raw_event.id,
                        schema_version="hira-hospital-info.v1",
                        source_updated_at=item.source_updated_at,
                    )
                )
                loaded += 1
            await session.commit()
            if limit is not None and loaded >= limit:
                break
            total_count = parse_total_count(payload)
            if page_no * page_size >= total_count:
                break
            page_no += 1
    return loaded


def main() -> None:
    """Run the source-backed synchronization command."""

    parser = argparse.ArgumentParser(description="Sync HIRA Chungbuk hospital basic records")
    parser.add_argument("--limit", type=int, help="Maximum number of hospitals to load for a controlled test run")
    parser.add_argument("--page-size", type=int, default=1000, help="HIRA page size, between 1 and 1000")
    args = parser.parse_args()
    loaded = asyncio.run(sync_hospitals(limit=args.limit, page_size=args.page_size))
    print(f"Loaded {loaded} source-backed hospital records.")


if __name__ == "__main__":
    main()
