"""Public operational-status contracts without credentials or raw payloads."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OperationalServiceStatus(BaseModel):
    """Configuration and observed state for one dependency."""

    model_config = ConfigDict(extra="forbid")

    configured: bool
    status: str
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    last_error: str | None = None


class OperationalDataCounts(BaseModel):
    """Aggregate database coverage used to explain readiness."""

    model_config = ConfigDict(extra="forbid")

    patients: int = Field(ge=0)
    hospitals: int = Field(ge=0)
    emergency_institutions: int = Field(ge=0)
    emergency_institutions_with_realtime: int = Field(ge=0)
    emergency_institutions_with_departments: int = Field(ge=0)
    emergency_institutions_with_equipment: int = Field(ge=0)
    emergency_institutions_with_capabilities: int = Field(ge=0)
    source_identities_verified: int = Field(ge=0)
    source_identities_unverified: int = Field(ge=0)
    route_snapshots: int = Field(ge=0)
    active_policies: int = Field(ge=0)


class OperationalReadiness(BaseModel):
    """Feature-level readiness; false values are explicit, not simulated."""

    model_config = ConfigDict(extra="forbid")

    chat_intake: bool
    voice_intake: bool
    hospital_candidates: bool
    live_routes: bool
    policy_recommendation: bool


class SystemStatusResponse(BaseModel):
    """Safe application status consumed by the dashboard."""

    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    mode: str
    environment: str
    services: dict[str, OperationalServiceStatus]
    data: OperationalDataCounts
    readiness: OperationalReadiness
    warnings: list[str]


class DataSourceStatusResponse(BaseModel):
    """One data-source registry record with computed freshness state."""

    model_config = ConfigDict(extra="forbid")

    source_name: str
    dataset_id: str | None
    provider_name: str
    enabled: bool
    schema_version: str | None
    last_success_at: datetime | None
    last_failure_at: datetime | None
    last_error: str | None
    status: str
    age_seconds: int | None = Field(default=None, ge=0)
    freshness_threshold_seconds: int | None = Field(default=None, ge=0)
    reason: str | None
