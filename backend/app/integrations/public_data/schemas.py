"""Generic public-data response envelopes; no guessed API fields."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class PublicDataRawEnvelope(BaseModel):
    """Raw response metadata for source registry and audit storage."""

    model_config = ConfigDict(extra="forbid")

    source_name: str
    dataset_id: str
    request_id: str
    fetched_at: datetime
    payload: Any

