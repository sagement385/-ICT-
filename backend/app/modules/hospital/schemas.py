"""Pydantic schemas for source-traceable hospital data."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HospitalLocation(BaseModel):
    """Hospital location without fallback coordinates."""

    model_config = ConfigDict(extra="forbid")

    latitude: float | None = Field(ge=-90, le=90)
    longitude: float | None = Field(ge=-180, le=180)
    address: str | None


class NearbyHospitalRequest(BaseModel):
    """Privacy-preserving nearby lookup based on an already stored incident."""

    model_config = ConfigDict(extra="forbid")

    incident_id: str = Field(min_length=1)
    radius_km: float = Field(default=10.0, ge=5.0, le=10.0)


class DataFreshness(BaseModel):
    """Freshness status based on source timestamps."""

    model_config = ConfigDict(extra="forbid")

    status: str
    observed_at: datetime | None
    reason: str | None


class EmergencyInstitutionProfileResponse(BaseModel):
    """Official emergency-institution registration and source provenance."""

    model_config = ConfigDict(extra="forbid")

    emergency_type_code: str | None
    emergency_type_name: str | None
    representative_phone: str | None
    emergency_phone: str | None
    source_name: str
    source_record_id: str
    raw_payload_id: str | None
    schema_version: str
    fetched_at: datetime
    source_updated_at: datetime | None
    match_method: str
    identity_verified: bool
    coordinate_warning: bool
    freshness: DataFreshness


class HospitalResponse(BaseModel):
    """Hospital response with provenance fields."""

    model_config = ConfigDict(extra="forbid")

    hospital_id: str
    hospital_name: str
    hospital_type_code: str | None
    location: HospitalLocation
    phone: str | None
    source_name: str
    source_record_id: str | None
    raw_payload_id: str | None
    schema_version: str
    source_updated_at: datetime | None
    freshness: DataFreshness
    emergency_profile: EmergencyInstitutionProfileResponse | None


class HospitalDepartmentResponse(BaseModel):
    """Verified department fields available to recommendation evaluation."""

    model_config = ConfigDict(extra="forbid")

    department_code: str | None
    department_name: str
    specialist_count: int | None = Field(ge=0)
    source_name: str | None
    source_record_id: str | None
    raw_payload_id: str | None
    schema_version: str | None
    source_updated_at: datetime | None
    fetched_at: datetime | None


class HospitalEquipmentResponse(BaseModel):
    """Verified equipment fields available to recommendation evaluation."""

    model_config = ConfigDict(extra="forbid")

    equipment_code: str | None
    equipment_name: str
    equipment_count: int | None = Field(ge=0)
    source_name: str | None
    source_record_id: str | None
    raw_payload_id: str | None
    schema_version: str | None
    source_updated_at: datetime | None
    fetched_at: datetime | None


class HospitalCapabilityResponse(BaseModel):
    """Verified care capability without inferred availability."""

    model_config = ConfigDict(extra="forbid")

    capability_code: str | None
    capability_name: str
    available: bool | None
    source_name: str | None
    source_record_id: str | None
    raw_payload_id: str | None
    schema_version: str | None
    source_updated_at: datetime | None
    fetched_at: datetime | None


class HospitalRealtimeStatusResponse(BaseModel):
    """Latest source-backed realtime status when one is available."""

    model_config = ConfigDict(extra="forbid")

    acceptance_status: str | None
    available_beds: int | None = Field(ge=0)
    source_name: str
    source_record_id: str | None
    raw_payload_id: str | None
    schema_version: str
    source_updated_at: datetime | None
    source_updated_at_raw: str | None
    source_timezone: str
    fetched_at: datetime
    freshness: DataFreshness


class HospitalCandidateResponse(HospitalResponse):
    """Hospital summary enriched for policy evaluation, not an automatic recommendation."""

    departments: list[HospitalDepartmentResponse]
    equipment: list[HospitalEquipmentResponse]
    capabilities: list[HospitalCapabilityResponse]
    realtime_status: HospitalRealtimeStatusResponse | None
