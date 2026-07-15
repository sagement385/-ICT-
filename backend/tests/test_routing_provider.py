"""Tests for documented Naver route summary and path parsing."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.integrations.common.base_client import RawExternalResponse
from app.modules.routing.provider import NaverRoutingProvider
from app.modules.routing.schemas import RouteQuery

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "route-test.json"


@pytest.mark.asyncio
async def test_naver_provider_preserves_documented_path() -> None:
    """The provider keeps path coordinates without inventing geometry."""

    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    response_payload = {
        "code": 0,
        "message": "TEST_SUCCESS",
        "route": {
            "traoptimal": [
                {
                    "summary": {
                        "distance": fixture["response"]["distance_meters"],
                        "duration": fixture["response"]["duration_seconds"] * 1000,
                    },
                    "path": fixture["response"]["path"],
                }
            ]
        },
    }

    class FakeClient:
        async def fetch_raw(self, path: str, params: dict[str, str]) -> RawExternalResponse:
            assert path == "/driving"
            assert params["option"] == "traoptimal"
            return RawExternalResponse(
                request_id="TEST_REQUEST_001",
                status_code=200,
                fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
                headers={},
                payload=response_payload,
            )

    result = await NaverRoutingProvider(client=FakeClient()).get_route(
        RouteQuery(**fixture["query"])
    )

    assert result.path == [(0.0, 0.0), (0.05, 0.0)]
    assert result.distance_meters == fixture["response"]["distance_meters"]
