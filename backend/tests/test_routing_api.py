"""Routing API tests that never call Naver or use operational coordinates."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.errors import ApplicationError
from app.main import app
from app.modules.routing.schemas import RouteQuery, RouteSnapshotData

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "route-test.json"


def test_route_api_returns_provider_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    """The route test endpoint exposes only the provider-neutral route contract."""

    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    class FakeProvider:
        async def get_route(self, query: RouteQuery) -> RouteSnapshotData:
            assert query.model_dump() == fixture["query"]
            return RouteSnapshotData(
                provider_name=fixture["response"]["provider_name"],
                distance_meters=fixture["response"]["distance_meters"],
                duration_seconds=fixture["response"]["duration_seconds"],
                traffic_summary=fixture["response"]["traffic_summary"],
                fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
            )

    monkeypatch.setattr("app.api.v1.routing.NaverRoutingProvider", FakeProvider)
    response = TestClient(app).post("/api/v1/routing/test", json=fixture["query"])

    assert response.status_code == 200
    assert response.json()["provider_name"] == fixture["response"]["provider_name"]
    assert response.json()["distance_meters"] == fixture["response"]["distance_meters"]


def test_route_api_rejects_half_coordinate_pair() -> None:
    """Invalid coordinate payloads fail before any external request is made."""

    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    invalid_query = {**fixture["query"], "origin_latitude": None}
    response = TestClient(app).post("/api/v1/routing/test", json=invalid_query)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REQUEST_VALIDATION_ERROR"


def test_route_batch_returns_successes_and_explicit_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """The map batch endpoint never fills failed destinations with fake routes."""

    class FakeProvider:
        async def get_route(self, query: RouteQuery) -> RouteSnapshotData:
            if query.destination_longitude == 2:
                raise ApplicationError(
                    code="ROUTE_DATA_UNAVAILABLE",
                    message="TEST route unavailable",
                )
            return RouteSnapshotData(
                provider_name="TEST_PROVIDER",
                distance_meters=100,
                duration_seconds=60,
                traffic_summary="TEST_TRAFFIC",
                fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
                path=[(0.0, 0.0), (1.0, 1.0)],
            )

    monkeypatch.setattr("app.api.v1.routing.NaverRoutingProvider", FakeProvider)
    response = TestClient(app).post(
        "/api/v1/routing/batch",
        json={
            "origin_latitude": 0,
            "origin_longitude": 0,
            "destinations": [
                {"hospital_id": "TEST_HOSPITAL_001", "latitude": 1, "longitude": 1},
                {"hospital_id": "TEST_HOSPITAL_002", "latitude": 1, "longitude": 2},
            ],
        },
    )

    assert response.status_code == 200
    assert len(response.json()["routes"]) == 1
    assert response.json()["routes"][0]["hospital_id"] == "TEST_HOSPITAL_001"
    assert response.json()["errors"] == [
        {
            "hospital_id": "TEST_HOSPITAL_002",
            "code": "ROUTE_DATA_UNAVAILABLE",
            "message": "TEST route unavailable",
        }
    ]
