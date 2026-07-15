"""Sample-backed HIRA basic-list parser and provider-neutral records."""

from datetime import datetime
from typing import Any
from xml.etree import ElementTree

from pydantic import BaseModel, ConfigDict

from app.core.errors import ApplicationError


class HiraBasicHospital(BaseModel):
    """Fields verified against the live HIRA basic-list XML response."""

    model_config = ConfigDict(extra="forbid")

    hospital_id: str
    hospital_name: str
    hospital_type_code: str | None
    hospital_type_name: str | None
    address: str | None
    phone: str | None
    latitude: float | None
    longitude: float | None
    region_code: str | None
    region_name: str | None
    source_updated_at: datetime | None


def parse_basic_hospitals(payload: Any, fetched_at: datetime | None = None) -> list[HiraBasicHospital]:
    """Parse only fields confirmed by the HIRA basic-list sample."""

    root = _parse_xml(payload)
    hospitals: list[HiraBasicHospital] = []
    for item in root.findall(".//item"):
        fields = {child.tag: child.text for child in item}
        hospital_id = fields.get("ykiho")
        hospital_name = fields.get("yadmNm")
        if not hospital_id or not hospital_name:
            continue
        hospitals.append(
            HiraBasicHospital(
                hospital_id=hospital_id,
                hospital_name=hospital_name,
                hospital_type_code=fields.get("clCd"),
                hospital_type_name=fields.get("clCdNm"),
                address=fields.get("addr"),
                phone=fields.get("telno"),
                latitude=_parse_float(fields.get("YPos")),
                longitude=_parse_float(fields.get("XPos")),
                region_code=fields.get("sidoCd"),
                region_name=fields.get("sidoCdNm"),
                source_updated_at=None,
            )
        )
    del fetched_at
    return hospitals


def parse_total_count(payload: Any) -> int:
    """Read the documented pagination count from a HIRA XML response."""

    root = _parse_xml(payload)
    value = root.findtext(".//totalCount")
    try:
        return int(value or "0")
    except ValueError:
        return 0


def _parse_xml(payload: Any) -> ElementTree.Element:
    """Parse the raw XML response without accepting guessed JSON fields."""

    if not isinstance(payload, str):
        raise ApplicationError(
            code="HIRA_RESPONSE_FORMAT_INVALID",
            message="HIRA 응답이 XML 문자열이 아닙니다.",
            details={},
        )
    try:
        return ElementTree.fromstring(payload)
    except ElementTree.ParseError as error:
        raise ApplicationError(
            code="HIRA_RESPONSE_PARSE_FAILED",
            message="HIRA 응답 XML을 해석할 수 없습니다.",
            details={},
        ) from error


def _parse_float(value: str | None) -> float | None:
    """Convert a confirmed coordinate field while preserving missing values."""

    if value is None or not value.strip():
        return None
    try:
        return float(value)
    except ValueError:
        return None
