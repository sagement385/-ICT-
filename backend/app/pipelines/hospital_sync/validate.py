"""Hospital validation stage reserved for sample-backed schemas."""

from typing import Any

from app.core.errors import ApplicationError


def validate(record: dict[str, Any]) -> dict[str, Any]:
    """Stop before validating unconfirmed provider field names."""

    del record
    raise ApplicationError(
        code="HOSPITAL_VALIDATOR_NOT_IMPLEMENTED",
        message="실제 병원 API 응답 샘플 기반 validator가 아직 없습니다.",
        details={},
    )

