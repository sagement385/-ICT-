"""Naver route request and raw response envelopes."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class NaverDirectionsRawEnvelope(BaseModel):
    """Raw response holder before a sample-based parser is approved."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    fetched_at: datetime
    payload: Any

