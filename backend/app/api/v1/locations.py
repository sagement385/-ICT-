"""Location conversion endpoints used by the chat intake flow."""

from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from app.core.dependencies import get_external_http_client
from app.core.errors import ApplicationError
from app.integrations.naver_maps.geocoding_client import NaverGeocodingClient

router = APIRouter(prefix="/locations", tags=["locations"])


class GeocodeRequest(BaseModel):
    """Address body that stays out of access-log query strings."""

    model_config = ConfigDict(extra="forbid")

    address: str = Field(min_length=1, max_length=500)


@router.get("/geocode", deprecated=True)
async def geocode_address(
    address: str = Query(min_length=1),
    http_client: httpx.AsyncClient = Depends(get_external_http_client),
) -> dict[str, Any]:
    """Convert an entered address only when Naver returns a verified result."""

    return await _geocode(address, http_client)


@router.post("/geocode")
async def geocode_address_private(
    request: GeocodeRequest,
    http_client: httpx.AsyncClient = Depends(get_external_http_client),
) -> dict[str, Any]:
    """Convert an address supplied in the body to avoid URL-based logging."""

    return await _geocode(request.address, http_client)


async def _geocode(address: str, http_client: httpx.AsyncClient) -> dict[str, Any]:
    """Convert an entered address only when Naver returns a verified result."""

    response = await NaverGeocodingClient(http_client=http_client).fetch_raw(address)
    payload = response.payload
    if not isinstance(payload, dict):
        raise ApplicationError(
            code="GEOCODING_RESPONSE_FORMAT_INVALID",
            message="네이버 주소 변환 응답이 JSON 객체가 아닙니다.",
            details={"request_id": response.request_id},
        )
    addresses = payload.get("addresses")
    if not isinstance(addresses, list) or not addresses or not isinstance(addresses[0], dict):
        raise ApplicationError(
            code="ADDRESS_NOT_FOUND",
            message="입력한 주소의 좌표를 확인하지 못했습니다.",
            status_code=404,
            details={},
        )
    result = addresses[0]
    latitude = _number(result.get("y"))
    longitude = _number(result.get("x"))
    if latitude is None or longitude is None:
        raise ApplicationError(
            code="GEOCODING_RESPONSE_SCHEMA_INVALID",
            message="주소 변환 응답에 좌표가 없습니다.",
            details={},
        )
    return {
        "address": result.get("roadAddress") or result.get("jibunAddress") or address,
        "latitude": latitude,
        "longitude": longitude,
        "source_name": "naver-geocoding",
        "fetched_at": response.fetched_at.isoformat(),
    }


def _number(value: object) -> float | None:
    """Convert a provider coordinate field without fallback coordinates."""

    if not isinstance(value, (str, int, float)):
        return None
    try:
        return float(value)
    except ValueError:
        return None
