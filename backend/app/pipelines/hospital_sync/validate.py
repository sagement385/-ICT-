"""Hospital validation stage for normalized HIRA records."""

from typing import Any

from app.integrations.hira.parser import HiraBasicHospital


def validate(record: dict[str, Any]) -> dict[str, Any]:
    """Validate one normalized HIRA record without filling missing values."""

    return HiraBasicHospital.model_validate(record).model_dump()
