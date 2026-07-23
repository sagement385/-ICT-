"""Routing API tests that never call Naver or use operational coordinates."""

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.main import app
from app.modules.routing.schemas import (
    RouteBatchError,
    RouteBatchItem,
    RouteBatchQuery,
    RouteBatchResponse,
    RouteQuery,
    RouteSnapshotData,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "route-test.json"


def test_route_api_returns_provider_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    """The route test endpoint exposes only the provider-neutral route contract."""

    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    class FakeProvider:
        def __init__(self, client: object) -> None:
            del client

        async def get_route(self, query: RouteQuery) -> RouteSnapshotData:
            assert query.model_dump() == fixture["query"]
            return RouteSnapshotData(
                provider_name=fixture["response"]["provider_name"],
                distance_meters=fixture["response"]["distance_meters"],
                duration_seconds=fixture["response"]["duration_seconds"],
                traffic_summary=fixture["response"]["traffic_summary"],
                fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
                source_name="TEST_PROVIDER",
                source_record_id="TEST_ROUTE_001",
                schema_version="test-route.v1",
            )

    monkeypatch.setattr("app.api.v1.routing.NaverRoutingProvider", FakeProvider)
    with TestClient(app) as client:
        response = client.post("/api/v1/routing/test", json=fixture["query"])

    assert response.status_code == 200
    assert response.json()["provider_name"] == fixture["response"]["provider_name"]
    assert response.json()["distance_meters"] == fixture["response"]["distance_meters"]


def test_route_api_rejects_half_coordinate_pair() -> None:
    """Invalid coordinate payloads fail before any external request is made."""

    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    invalid_query = {**fixture["query"], "origin_latitude": None}
    with TestClient(app) as client:
        response = client.post("/api/v1/routing/test", json=invalid_query)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REQUEST_VALIDATION_ERROR"


def test_route_batch_returns_successes_and_explicit_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """The map batch endpoint never fills failed destinations with fake routes."""

    class FakeService:
        def __init__(self, session: AsyncSession, provider: object) -> None:
            del session, provider

        async def get_batch(self, query: RouteBatchQuery) -> RouteBatchResponse:
            assert query.incident_id == "TEST_PATIENT_001"
            assert query.hospital_ids == ["TEST_HOSPITAL_001", "TEST_HOSPITAL_002"]
            route = RouteSnapshotData(
                provider_name="TEST_PROVIDER",
                distance_meters=100,
                duration_seconds=60,
                traffic_summary="TEST_TRAFFIC",
                fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
                path=[(0.0, 0.0), (1.0, 1.0)],
                source_name="TEST_PROVIDER",
                source_record_id="TEST_ROUTE_001",
                schema_version="test-route.v1",
            )
            return RouteBatchResponse(
                routes=[
                    RouteBatchItem(
                        hospital_id="TEST_HOSPITAL_001",
                        route=route,
                        cache_status="miss",
                    )
                ],
                errors=[
                    RouteBatchError(
                        hospital_id="TEST_HOSPITAL_002",
                        code="ROUTE_DATA_UNAVAILABLE",
                        message="TEST route unavailable",
                    )
                ],
                generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            )

    async def test_db_session() -> AsyncIterator[AsyncSession]:
        """Provide a non-operational session boundary; this request does not persist."""

        yield AsyncMock(spec=AsyncSession)

    monkeypatch.setattr("app.api.v1.routing.RoutingService", FakeService)
    app.dependency_overrides[get_db_session] = test_db_session
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/routing/batch",
                json={
                    "incident_id": "TEST_PATIENT_001",
                    "hospital_ids": ["TEST_HOSPITAL_001", "TEST_HOSPITAL_002"],
                },
            )
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 200
    assert len(response.json()["routes"]) == 1
    assert response.json()["routes"][0]["hospital_id"] == "TEST_HOSPITAL_001"
    assert response.json()["routes"][0]["cache_status"] == "miss"
    assert response.json()["errors"] == [
        {
            "hospital_id": "TEST_HOSPITAL_002",
            "code": "ROUTE_DATA_UNAVAILABLE",
            "message": "TEST route unavailable",
        }
    ]
