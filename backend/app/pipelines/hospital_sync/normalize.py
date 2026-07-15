"""Hospital normalization stage awaiting verified source samples."""

from typing import Any

from app.core.errors import ApplicationError


def normalize(payload: Any) -> dict[str, Any]:
    """Stop before guessing provider field names."""

    del payload
    raise ApplicationError(
        code="HOSPITAL_PARSER_NOT_IMPLEMENTED",
        message="실제 병원 API 응답 샘플 기반 정규화가 아직 없습니다.",
        details={},
    )

