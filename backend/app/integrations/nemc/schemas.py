"""Typed fields confirmed by the NMC realtime response sample."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class NemcRealtimeRecord(BaseModel):
    """A source record with raw status fields kept for later official-code mapping."""

    model_config = ConfigDict(extra="forbid")

    source_record_id: str
    institution_name: str | None
    source_updated_at: datetime | None
    source_updated_at_raw: str | None
    source_timezone: str
    raw_fields: dict[str, Any]


class NemcEmergencyInstitutionRecord(BaseModel):
    """Emergency-institution identity fields confirmed by the live list response."""

    model_config = ConfigDict(extra="forbid")

    source_record_id: str
    institution_name: str
    address: str | None
    emergency_type_code: str | None
    emergency_type_name: str | None
    representative_phone: str | None
    emergency_phone: str | None
    latitude: float | None
    longitude: float | None
    raw_fields: dict[str, Any]
