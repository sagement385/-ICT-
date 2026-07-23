"""XML parser for NMC responses, preserving unconfirmed status codes."""

from datetime import datetime
from typing import Any
from xml.etree import ElementTree
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.errors import ApplicationError
from app.integrations.nemc.schemas import (
    NemcEmergencyInstitutionRecord,
    NemcRealtimeRecord,
)


def parse_realtime_records(
    payload: Any,
    source_timezone: str | None = None,
) -> list[NemcRealtimeRecord]:
    """Parse confirmed identity and timestamp fields while retaining every raw item field."""

    root = _parse_xml(payload)
    records: list[NemcRealtimeRecord] = []
    for item in root.findall(".//item"):
        fields = {child.tag: child.text for child in item}
        source_record_id = fields.get("hpid")
        if not source_record_id:
            continue
        source_updated_at_raw = fields.get("hvidate")
        records.append(
            NemcRealtimeRecord(
                source_record_id=source_record_id,
                institution_name=fields.get("dutyName"),
                source_updated_at=_parse_timestamp(
                    source_updated_at_raw,
                    source_timezone,
                ),
                source_updated_at_raw=source_updated_at_raw,
                source_timezone=source_timezone or "unknown",
                raw_fields=fields,
            )
        )
    return records


def parse_emergency_institutions(payload: Any) -> list[NemcEmergencyInstitutionRecord]:
    """Parse only fields observed in the live emergency-institution list response."""

    root = _parse_xml(payload)
    records: list[NemcEmergencyInstitutionRecord] = []
    for item in root.findall(".//item"):
        fields = {child.tag: child.text for child in item}
        source_record_id = fields.get("hpid")
        institution_name = fields.get("dutyName")
        if not source_record_id or not institution_name:
            continue
        records.append(
            NemcEmergencyInstitutionRecord(
                source_record_id=source_record_id,
                institution_name=institution_name,
                address=fields.get("dutyAddr"),
                emergency_type_code=fields.get("dutyEmcls"),
                emergency_type_name=fields.get("dutyEmclsName"),
                representative_phone=fields.get("dutyTel1"),
                emergency_phone=fields.get("dutyTel3"),
                latitude=_parse_float(fields.get("wgs84Lat")),
                longitude=_parse_float(fields.get("wgs84Lon")),
                raw_fields=fields,
            )
        )
    return records


def parse_total_count(payload: Any) -> int:
    """Read the pagination count from a verified NEMC response envelope."""

    root = _parse_xml(payload)
    value = root.findtext(".//totalCount")
    if value is None:
        raise ApplicationError(
            code="NEMC_PAGINATION_INVALID",
            message="국립중앙의료원 응답에 전체 건수가 없습니다.",
            details={},
        )
    try:
        total_count = int(value)
    except ValueError as error:
        raise ApplicationError(
            code="NEMC_PAGINATION_INVALID",
            message="국립중앙의료원 응답의 전체 건수가 올바르지 않습니다.",
            details={},
        ) from error
    if total_count < 0:
        raise ApplicationError(
            code="NEMC_PAGINATION_INVALID",
            message="국립중앙의료원 응답의 전체 건수가 음수입니다.",
            details={},
        )
    return total_count


def calculate_total_pages(total_count: int, page_size: int) -> int:
    """Return an explicit page count while retaining the mandatory first request."""

    if page_size < 1:
        raise ValueError("page_size must be greater than zero")
    normalized_count = max(total_count, 0)
    return max(1, (normalized_count + page_size - 1) // page_size)


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


def _parse_timestamp(
    value: str | None,
    source_timezone: str | None,
) -> datetime | None:
    """Parse a source timestamp only when its timezone is explicitly configured."""

    if not value or not source_timezone:
        return None
    try:
        timezone = ZoneInfo(source_timezone)
    except ZoneInfoNotFoundError as error:
        raise ApplicationError(
            code="NEMC_SOURCE_TIMEZONE_INVALID",
            message="NEMC 원본 시간대 설정을 확인할 수 없습니다.",
            details={"setting_name": "NEMC_SOURCE_TIMEZONE"},
        ) from error
    try:
        return datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=timezone)
    except ValueError:
        return None


def _parse_float(value: str | None) -> float | None:
    """Parse a confirmed coordinate while preserving absent or malformed values."""

    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None
