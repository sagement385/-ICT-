"""Hospital normalization stage backed by the verified HIRA basic sample."""

from datetime import datetime
from typing import Any

from app.integrations.hira.parser import HiraBasicHospital, parse_basic_hospitals


def normalize(payload: Any, fetched_at: datetime) -> list[HiraBasicHospital]:
    """Normalize fields confirmed by HIRA basic-list responses."""

    return parse_basic_hospitals(payload, fetched_at)
