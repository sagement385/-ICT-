"""XML parser for NMC responses, preserving unconfirmed status codes."""

from datetime import datetime
from typing import Any
from xml.etree import ElementTree

from app.core.errors import ApplicationError
from app.integrations.nemc.schemas import NemcRealtimeRecord


def parse_realtime_records(payload: Any) -> list[NemcRealtimeRecord]:
    """Parse confirmed identity and timestamp fields while retaining every raw item field."""

    root = _parse_xml(payload)
    records: list[NemcRealtimeRecord] = []
    for item in root.findall(".//item"):
        fields = {child.tag: child.text for child in item}
        source_record_id = fields.get("hpid")
        if not source_record_id:
            continue
        records.append(
            NemcRealtimeRecord(
                source_record_id=source_record_id,
                institution_name=fields.get("dutyName"),
                source_updated_at=_parse_timestamp(fields.get("hvidate")),
                raw_fields=fields,
            )
        )
    return records


def parse_total_count(payload: Any) -> int:
    """Read the pagination count from a verified NEMC response envelope."""

    root = _parse_xml(payload)
    value = root.findtext(".//totalCount")
    try:
        return int(value or "0")
    except ValueError:
        return 0


def parse_region_record_ids(payload: Any, region_keyword: str) -> set[str]:
    """Return source IDs whose confirmed basic address contains the region keyword."""

    root = _parse_xml(payload)
    record_ids: set[str] = set()
    for item in root.findall(".//item"):
        fields = {child.tag: child.text for child in item}
        source_record_id = fields.get("hpid")
        if source_record_id and region_keyword in (fields.get("dutyAddr") or ""):
            record_ids.add(source_record_id)
    return record_ids


def _parse_xml(payload: Any) -> ElementTree.Element:
    """Parse a raw XML string and expose provider errors explicitly."""

    if not isinstance(payload, str):
        raise ApplicationError(
            code="NEMC_RESPONSE_FORMAT_INVALID",
            message="국립중앙의료원 응답이 XML 문자열이 아닙니다.",
            details={},
        )
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError as error:
        raise ApplicationError(
            code="NEMC_RESPONSE_PARSE_FAILED",
            message="국립중앙의료원 응답 XML을 해석할 수 없습니다.",
            details={},
        ) from error
    result_code = root.findtext(".//header/resultCode")
    if result_code is not None and result_code != "00":
        raise ApplicationError(
            code="NEMC_PROVIDER_ERROR",
            message="국립중앙의료원 API가 성공이 아닌 결과 코드를 반환했습니다.",
            details={"provider_code": result_code},
        )
    return root


def _parse_timestamp(value: str | None) -> datetime | None:
    """Parse the confirmed YYYYMMDDHHMMSS source timestamp."""

    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d%H%M%S").astimezone()
    except ValueError:
        return None
