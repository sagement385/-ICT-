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
    raw_fields: dict[str, Any]
