"""Integration tests for the generic policy engine using TEST-only fixtures."""

import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.freshness import evaluate_freshness
from app.modules.hospital.models import Hospital, HospitalEmergencyProfile
from app.modules.patient.models import PatientCase, PatientSymptom
from app.modules.recommendation.models import (
    RecommendationPolicy,
    RecommendationResult,
    RecommendationRun,
    RecommendationWeight,
)
from app.modules.recommendation.recommendation_service import RecommendationService
from app.modules.routing.models import RouteSnapshot
from app.modules.routing.schemas import RouteQuery, RouteSnapshotData

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "recommendation-policy-engine-test.json"


def load_fixture() -> dict[str, Any]:
    """Load the isolated recommendation fixture."""

    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_freshness_requires_a_timestamp_and_threshold() -> None:
    """Freshness is never assumed when either input is missing."""

    fixture = load_fixture()
    now = datetime.fromisoformat(fixture["now"])

    assert evaluate_freshness(None, fixture["freshness_threshold_seconds"], now=now).status == "unknown"
    assert evaluate_freshness(now, None, now=now).status == "unknown"
    assert (
        evaluate_freshness(
            now,
            fixture["freshness_threshold_seconds"],
            now=now,
        ).status
        == "fresh"
    )


@pytest.mark.asyncio
async def test_policy_pipeline_persists_and_serializes_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicitly configured TEST policy can score, persist, and load latest."""

    fixture = load_fixture()
    now = datetime.fromisoformat(fixture["now"])
    threshold = fixture["freshness_threshold_seconds"]
    monkeypatch.setattr(
        "app.modules.recommendation.feature_builder.get_settings",
        lambda: SimpleNamespace(
            hospital_data_max_age_seconds=threshold,
            route_data_max_age_seconds=threshold,
            hospital_status_max_age_seconds=threshold,
            emergency_institution_data_max_age_seconds=threshold,
        ),
    )

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    class TestRealtimeProvider:
        async def load(self, hospital_ids: list[str]) -> dict[str, dict[str, Any]]:
            assert hospital_ids
            return {}

    route_by_longitude = {
        item["longitude"]: item
        for item in fixture["hospitals"]
    }

    class TestRouteProvider:
        async def get_route(self, query: RouteQuery) -> RouteSnapshotData:
            hospital = route_by_longitude[query.destination_longitude]
            return RouteSnapshotData(
                provider_name="TEST_ROUTE_PROVIDER",
                distance_meters=hospital["distance_meters"],
                duration_seconds=hospital["duration_seconds"],
                traffic_summary="TEST_TRAFFIC_SUMMARY",
                fetched_at=now,
                path=None,
                source_name="TEST_ROUTE_SOURCE",
                source_record_id=f"TEST_ROUTE_{hospital['hospital_id']}",
                raw_payload_id=None,
                schema_version="test-route.v1",
                source_metadata={},
            )

    async with session_factory() as session:
        patient = fixture["patient"]
        session.add(
            PatientCase(
                incident_id=patient["incident_id"],
                consciousness_status=None,
                breathing_status=None,
                bleeding_status=None,
                urgency_level=None,
                latitude=patient["latitude"],
                longitude=patient["longitude"],
                address_text=None,
                source_model_name="TEST_SOURCE_MODEL",
                source_model_version="TEST_SOURCE_VERSION",
                received_at=now,
            )
        )
        session.add(
            PatientSymptom(
                incident_id=patient["incident_id"],
                symptom_code=patient["symptom_code"],
                symptom_label=patient["symptom_label"],
                confidence=None,
            )
        )
        for item in fixture["hospitals"]:
            session.add(
                Hospital(
                    hospital_id=item["hospital_id"],
                    hospital_name=item["hospital_name"],
                    hospital_type_code=None,
                    address=None,
                    latitude=item["latitude"],
                    longitude=item["longitude"],
                    phone=None,
                    source_name="TEST_HOSPITAL_SOURCE",
                    source_record_id=item["hospital_id"],
                    raw_payload_id=None,
                    schema_version="test-hospital.v1",
                    source_updated_at=now,
                )
            )
            session.add(
                HospitalEmergencyProfile(
                    hospital_id=item["hospital_id"],
                    source_name="TEST_EMERGENCY_SOURCE",
                    source_record_id=f"TEST_NEMC_{item['hospital_id']}",
                    source_institution_name=item["hospital_name"],
                    source_address=None,
                    source_latitude=item["latitude"],
                    source_longitude=item["longitude"],
                    emergency_type_code="TEST_EMERGENCY_TYPE",
                    emergency_type_name="TEST_EMERGENCY_TYPE_NAME",
                    representative_phone=None,
                    emergency_phone=None,
                    match_method="TEST_MATCH_METHOD",
                    active=True,
                    coordinate_distance_meters=0,
                    coordinate_warning=False,
                    raw_payload_id=None,
                    schema_version="test-emergency.v1",
                    source_updated_at=now,
                    fetched_at=now,
                )
            )
        policy_data = fixture["policy"]
        policy = RecommendationPolicy(
            policy_name=policy_data["policy_name"],
            policy_version=policy_data["policy_version"],
            enabled=True,
            evidence_source="TEST_EVIDENCE_SOURCE",
            effective_from=None,
            effective_to=None,
        )
        session.add(policy)
        await session.flush()
        session.add(
            RecommendationWeight(
                policy_id=policy.id,
                factor_name=policy_data["factor_name"],
                weight_value=policy_data["weight_value"],
                enabled=True,
                source_field=policy_data["source_field"],
                direction=policy_data["direction"],
                normalization=policy_data["normalization"],
                required=True,
                missing_data_behavior="fail_run",
                stale_data_behavior="fail_run",
                hard_exclusion=False,
                explanation=policy_data["explanation"],
                configuration_json={
                    "minimum": policy_data["minimum"],
                    "maximum": policy_data["maximum"],
                },
            )
        )
        await session.commit()

        service = RecommendationService(
            session,
            realtime_provider=TestRealtimeProvider(),
            route_provider=TestRouteProvider(),
        )
        response = await service.run(patient["incident_id"], limit=2)
        latest = await service.latest(patient["incident_id"])

        assert [item.hospital_id for item in response.recommended_hospitals] == [
            "TEST_HOSPITAL_001",
            "TEST_HOSPITAL_002",
        ]
        assert latest.recommendation_run_id == response.recommendation_run_id
        assert latest.policy == response.policy
        assert [item.hospital_id for item in latest.recommended_hospitals] == [
            item.hospital_id for item in response.recommended_hospitals
        ]
        assert [item.total_score for item in latest.recommended_hospitals] == [
            item.total_score for item in response.recommended_hospitals
        ]
        assert latest.warnings == response.warnings
        assert (
            await session.scalar(select(func.count()).select_from(RecommendationRun))
        ) == 1
        assert (
            await session.scalar(select(func.count()).select_from(RecommendationResult))
        ) == 2
        assert (
            await session.scalar(select(func.count()).select_from(RouteSnapshot))
        ) == 2

    await engine.dispose()
