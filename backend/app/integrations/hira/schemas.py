"""Raw HIRA payload contracts without guessed provider fields."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class HiraRawEnvelope(BaseModel):
    """Stored response metadata before an approved parser is added."""

    model_config = ConfigDict(extra="forbid")

    source_name: str
    request_id: str
    fetched_at: datetime
    payload: Any

