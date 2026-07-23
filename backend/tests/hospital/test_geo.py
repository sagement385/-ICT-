"""Tests for the provider-neutral hospital distance boundary."""

import json
from datetime import UTC, datetime
from pathlib import Path

from app.modules.hospital.geo import distance_km
from app.modules.hospital.models import Hospital
from app.modules.patient.schemas import PatientEventRequest
from app.modules.recommendation.candidate_filter import CandidateFilter


def test_distance_km_respects_test_fixture_radius() -> None:
    """The shared distance calculation distinguishes fixture points around 10 km."""

    fixture_path = Path(__file__).parents[1] / "fixtures" / "geo-test.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    origin = fixture["origin"]
    inside = fixture["inside_radius"]
    outside = fixture["outside_radius"]
    radius = fixture["radius_km"]

    assert distance_km(origin["latitude"], origin["longitude"], inside["latitude"], inside["longitude"]) <= radius
    assert distance_km(origin["latitude"], origin["longitude"], outside["latitude"], outside["longitude"]) > radius


def test_candidate_filter_excludes_fixture_hospitals_outside_radius() -> None:
    """Candidate filtering keeps only coordinate-backed hospitals within the configured radius."""

    fixture_path = Path(__file__).parents[1] / "fixtures" / "geo-test.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    origin = fixture["origin"]
    inside = fixture["inside_radius"]
    outside = fixture["outside_radius"]
    patient = PatientEventRequest(
        incident_id="TEST_PATIENT_001",
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        location={"latitude": origin["latitude"], "longitude": origin["longitude"], "address_text": None},
        symptoms=[],
        consciousness_status=None,
        breathing_status=None,
        bleeding_status=None,
        urgency_level=None,
        source={"model_name": "TEST_MODEL", "model_version": "TEST_VERSION"},
    )
    hospitals = [
        Hospital(
            hospital_id="TEST_HOSPITAL_INSIDE",
            hospital_name="TEST_HOSPITAL_INSIDE",
            latitude=inside["latitude"],
            longitude=inside["longitude"],
            source_name="TEST_SOURCE",
            schema_version="TEST_SCHEMA_V1",
        ),
        Hospital(
            hospital_id="TEST_HOSPITAL_OUTSIDE",
            hospital_name="TEST_HOSPITAL_OUTSIDE",
            latitude=outside["latitude"],
            longitude=outside["longitude"],
            source_name="TEST_SOURCE",
            schema_version="TEST_SCHEMA_V1",
        ),
    ]

    selected = CandidateFilter().filter(patient, hospitals, None)

    assert [hospital.hospital_id for hospital in selected] == ["TEST_HOSPITAL_INSIDE"]
