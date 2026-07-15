"""Application errors and the stable JSON error envelope."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApplicationError(Exception):
    """A safe, serializable domain error intended for API responses."""

    code: str
    message: str
    status_code: int = 503
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__init__(self.message)


def error_body(error: ApplicationError, request_id: str) -> dict[str, Any]:
    """Build the common error response without exposing credentials or raw payloads."""

    return {
        "error": {
            "code": error.code,
            "message": error.message,
            "details": error.details,
            "request_id": request_id,
        }
    }

