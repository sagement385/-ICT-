"""Hospital normalization stage backed by the verified HIRA basic sample."""

from typing import Any

from app.integrations.hira.parser import parse_basic_hospitals


def normalize(payload: Any) -> list[dict[str, Any]]:
    """Normalize fields confirmed by HIRA basic-list responses."""

    return [hospital.model_dump() for hospital in parse_basic_hospitals(payload)]
