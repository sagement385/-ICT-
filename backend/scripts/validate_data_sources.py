"""Validate configured HIRA and NEMC source connectivity without database writes."""

import argparse
import asyncio
import json
from typing import Any

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.integrations.hira.client import HiraClient
from app.integrations.hira.parser import parse_basic_hospitals
from app.integrations.nemc.client import NemcEmergencyClient
from app.integrations.nemc.parser import parse_realtime_records, parse_total_count


async def validate_hira() -> dict[str, Any]:
    """Fetch and parse one configured-region HIRA page without persisting it."""

    settings = get_settings()
    response = await HiraClient().fetch_basic_page(
        page_no=1,
        num_of_rows=1,
        sido_code=settings.chungbuk_sido_code,
    )
    records = parse_basic_hospitals(response.payload, response.fetched_at)
    return {
        "status": "ok",
        "http_status": response.status_code,
        "record_count": len(records),
        "region_code": settings.chungbuk_sido_code,
    }


async def validate_nemc() -> dict[str, Any]:
    """Fetch and parse one NEMC realtime page without inferring status meanings."""

    response = await NemcEmergencyClient().fetch_realtime_status(page_no=1, num_of_rows=1)
    records = parse_realtime_records(response.payload)
    return {
        "status": "ok",
        "http_status": response.status_code,
        "record_count": len(records),
        "source_total_count": parse_total_count(response.payload),
    }


async def validate_sources(source: str) -> dict[str, dict[str, Any]]:
    """Run selected source checks and return safe summaries only."""

    validators = {"hira": validate_hira, "nemc": validate_nemc}
    selected = validators.keys() if source == "all" else (source,)
    results: dict[str, dict[str, Any]] = {}
    for name in selected:
        try:
            results[name] = await validators[name]()
        except ApplicationError as error:
            results[name] = {
                "status": "error",
                "code": error.code,
                "details": error.details,
            }
        except Exception:
            results[name] = {
                "status": "error",
                "code": "SOURCE_VALIDATION_FAILED",
                "details": {},
            }
    return results


def main() -> None:
    """Run source validation checks."""

    parser = argparse.ArgumentParser(description="Validate HIRA and NEMC API connectivity")
    parser.add_argument("--source", choices=("all", "hira", "nemc"), default="all")
    args = parser.parse_args()
    results = asyncio.run(validate_sources(args.source))
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if any(result.get("status") != "ok" for result in results.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
