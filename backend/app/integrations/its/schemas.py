"""Raw ITS file and response envelopes."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ItsRawEnvelope(BaseModel):
    """Raw ITS payload before a verified file/schema parser exists."""

    model_config = ConfigDict(extra="forbid")

    source_name: str
    fetched_at: datetime
    payload: Any

