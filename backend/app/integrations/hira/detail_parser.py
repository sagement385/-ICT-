"""Parsers for HIRA detail fields verified against live API responses."""

from __future__ import annotations

import json
from typing import Any
from xml.etree import ElementTree

from pydantic import BaseModel, ConfigDict

from app.core.errors import ApplicationError


class HiraDepartmentRecord(BaseModel):
    """A department row whose code and specialist field came from HIRA."""

    model_config = ConfigDict(extra="forbid")

    department_code: str
    department_name: str
    specialist_count: int | None


class HiraCapabilityRecord(BaseModel):
    """A special-diagnosis row; availability remains unknown unless sourced."""

    model_config = ConfigDict(extra="forbid")

    capability_code: str
    capability_name: str
    available: bool | None


class HiraEquipmentRecord(BaseModel):
    """A medical-equipment row confirmed against a live HIRA response."""

    model_config = ConfigDict(extra="forbid")

    equipment_code: str
    equipment_name: str
    equipment_count: int | None


class HiraDetailParseResult(BaseModel):
    """Normalized rows plus unmodified detail items for unsupported mappings."""

    model_config = ConfigDict(extra="forbid")

    departments: list[HiraDepartmentRecord]
    capabilities: list[HiraCapabilityRecord]
    equipment: list[HiraEquipmentRecord]
    raw_items: list[dict[str, str | None]]


def parse_detail(endpoint: str, payload: Any) -> HiraDetailParseResult:
    """Parse only fields confirmed for the supplied HIRA detail endpoint."""

    items = _extract_items(payload)
    if endpoint == "getSpcSbjtSdrInfo2.8":
        departments = _parse_departments(items, "dtlSdrCnt")
        return HiraDetailParseResult(
            departments=departments,
            capabilities=[],
            equipment=[],
            raw_items=items,
        )

    if endpoint == "getDgsbjtInfo2.8":
        departments = _parse_departments(items, "dgsbjtPrSdrCnt")
        return HiraDetailParseResult(
            departments=departments,
            capabilities=[],
            equipment=[],
            raw_items=items,
        )

    if endpoint == "getSpclDiagInfo2.8":
        capabilities = _parse_capabilities(items)
        return HiraDetailParseResult(
            departments=[],
            capabilities=capabilities,
            equipment=[],
            raw_items=items,
        )

    if endpoint == "getMedOftInfo2.8":
        equipment = _parse_equipment(items)
        return HiraDetailParseResult(
            departments=[],
            capabilities=[],
            equipment=equipment,
            raw_items=items,
        )

    return HiraDetailParseResult(
        departments=[],
        capabilities=[],
        equipment=[],
        raw_items=items,
    )


def _parse_departments(items: list[dict[str, str | None]], count_field: str) -> list[HiraDepartmentRecord]:
    """Map a verified department endpoint to the shared department table shape."""

    departments: list[HiraDepartmentRecord] = []
    for item in items:
        department_code = item.get("dgsbjtCd")
        department_name = item.get("dgsbjtCdNm")
        if department_code is None or department_name is None:
            continue
        departments.append(
            HiraDepartmentRecord(
                department_code=department_code,
                department_name=department_name,
                specialist_count=_parse_int(item.get(count_field)),
            )
        )
    return departments


def _parse_capabilities(items: list[dict[str, str | None]]) -> list[HiraCapabilityRecord]:
    """Map a verified special-diagnosis endpoint without inferring availability."""

    capabilities: list[HiraCapabilityRecord] = []
    for item in items:
        capability_code = item.get("srchCd")
        capability_name = item.get("srchCdNm")
        if capability_code is None or capability_name is None:
            continue
        capabilities.append(
            HiraCapabilityRecord(
                capability_code=capability_code,
                capability_name=capability_name,
                available=None,
            )
        )
    return capabilities


def _parse_equipment(items: list[dict[str, str | None]]) -> list[HiraEquipmentRecord]:
    """Map only the live-sample-confirmed medical equipment fields."""

    equipment: list[HiraEquipmentRecord] = []
    for item in items:
        equipment_code = item.get("oftCd")
        equipment_name = item.get("oftCdNm")
        if equipment_code is None or equipment_name is None:
            continue
        equipment.append(
            HiraEquipmentRecord(
                equipment_code=equipment_code,
                equipment_name=equipment_name,
                equipment_count=_parse_int(item.get("oftCnt")),
            )
        )
    return equipment


def _extract_items(payload: Any) -> list[dict[str, str | None]]:
    """Extract provider items from the verified XML or JSON response envelope."""

    if isinstance(payload, str):
        try:
            root = ElementTree.fromstring(payload)
        except ElementTree.ParseError as error:
            raise ApplicationError(
                code="HIRA_RESPONSE_PARSE_FAILED",
                message="HIRA 상세 응답 XML을 해석할 수 없습니다.",
                details={},
            ) from error
        _validate_result_code(root.findtext(".//header/resultCode"))
        return [{child.tag: child.text for child in item} for item in root.findall(".//item")]

    if isinstance(payload, dict):
        try:
            response = payload["response"]
            header = response.get("header", {})
            if isinstance(header, dict):
                _validate_result_code(_to_optional_text(header.get("resultCode")))
            items: Any = response["body"].get("items", {}).get("item", [])
        except (AttributeError, KeyError, TypeError) as error:
            raise ApplicationError(
                code="HIRA_RESPONSE_FORMAT_INVALID",
                message="HIRA 상세 응답 JSON 구조가 예상과 다릅니다.",
                details={},
            ) from error
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list):
            return []
        return [
            {str(key): _to_optional_text(value) for key, value in item.items()}
            for item in items
            if isinstance(item, dict)
        ]

    raise ApplicationError(
        code="HIRA_RESPONSE_FORMAT_INVALID",
        message="HIRA 상세 응답 형식을 지원하지 않습니다.",
        details={"payload_type": type(payload).__name__},
    )


def _validate_result_code(result_code: str | None) -> None:
    """Reject a non-success result code confirmed by the provider envelope."""

    if result_code is not None and result_code != "00":
        raise ApplicationError(
            code="HIRA_PROVIDER_ERROR",
            message="HIRA가 성공이 아닌 결과 코드를 반환했습니다.",
            details={"provider_code": result_code},
        )


def _to_optional_text(value: Any) -> str | None:
    """Convert JSON scalar values to the raw string representation used by models."""

    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _parse_int(value: str | None) -> int | None:
    """Parse a confirmed numeric source field without inventing a default."""

    if value is None or not value.strip():
        return None
    try:
        return int(value)
    except ValueError:
        return None
