"""Hospital validation stage for normalized HIRA records."""

from app.integrations.hira.parser import HiraBasicHospital


def validate(record: HiraBasicHospital) -> HiraBasicHospital:
    """Validate one normalized HIRA record without filling missing values."""

    return HiraBasicHospital.model_validate(record.model_dump())
