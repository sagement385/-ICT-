"""Pydantic contracts for recommendation requests and persisted results."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RecommendationRequest(BaseModel):
    """Request options; the incident identifier comes only from the URL path."""

    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=3, ge=1, le=3)


class PolicyResponse(BaseModel):
    """Policy identity attached to a recommendation result."""

    policy_name: str
    policy_version: str


class TravelTimeResponse(BaseModel):
    """Provider-normalized travel time."""

    duration_seconds: int = Field(ge=0)
    distance_meters: int = Field(ge=0)
    provider_name: str
    fetched_at: datetime


class RecommendedHospitalResponse(BaseModel):
    """One ranked hospital result with explanations and freshness."""

    rank: int
    hospital_id: str
    hospital_name: str
    location: dict[str, Any]
    total_score: float
    score_breakdown: dict[str, Any]
    travel_time: TravelTimeResponse | None
    recommendation_reasons: list[str]
    data_freshness: dict[str, Any]


class RecommendationResultResponse(BaseModel):
    """Stable response envelope; no response is created without real inputs."""

    incident_id: str
    recommendation_run_id: str
    generated_at: datetime
    policy: PolicyResponse
    recommended_hospitals: list[RecommendedHospitalResponse]
    warnings: list[str]
