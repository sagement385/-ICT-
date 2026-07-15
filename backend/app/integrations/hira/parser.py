"""Parser interface intentionally left unimplemented until samples are registered."""

from typing import Any, Protocol

from app.core.errors import ApplicationError


class HiraParser(Protocol):
    """Convert one verified HIRA raw payload into a domain record."""

    def parse(self, payload: Any) -> dict[str, Any]:
        """Parse only fields proven by an approved fixture."""


def parser_not_configured() -> None:
    """Raise the explicit error used before a source sample-based parser exists."""

    raise ApplicationError(
        code="HIRA_PARSER_NOT_IMPLEMENTED",
        message="HIRA 실제 응답 샘플 기반 parser가 아직 없습니다.",
        details={},
    )

