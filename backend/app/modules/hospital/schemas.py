"""Pydantic schemas for source-traceable hospital data."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HospitalLocation(BaseModel):
    """Hospital location without fallback coordinates."""

    model_config = ConfigDict(extra="forbid")

    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    address: str | None = None


class DataFreshness(BaseModel):
    """Freshness status based on source timestamps."""

    model_config = ConfigDict(extra="forbid")

    status: str
    observed_at: datetime | None = None
    reason: str | None = None


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

