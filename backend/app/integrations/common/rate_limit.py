"""Rate-limit response classification and process-local call budgets."""

import asyncio

from app.core.errors import ApplicationError


def is_rate_limited(status_code: int) -> bool:
    """Return whether a provider asks the caller to slow down."""

    return status_code in {408, 425, 429, 503}


class CallBudget:
    """Reserve calls with an optional process-local safety cap."""

    def __init__(self, limit: int | None) -> None:
        self.limit = limit
        self.used = 0
        self._lock = asyncio.Lock()

    async def reserve(self) -> None:
        """Reserve one call or raise a visible quota error."""

        async with self._lock:
            if self.limit is not None and self.used >= self.limit:
                raise ApplicationError(
                    code="ROUTE_API_CALL_LIMIT_REACHED",
                    message="네이버 경로 API 테스트 호출 한도에 도달했습니다.",
                    status_code=429,
                    details={"calls_used": self.used, "calls_limit": self.limit},
                )
            self.used += 1


_shared_budgets: dict[tuple[str, int | None], CallBudget] = {}


def get_shared_budget(name: str, limit: int | None) -> CallBudget:
    """Return one process-local budget shared by all clients of a provider."""

    key = (name, limit)
    if key not in _shared_budgets:
        _shared_budgets[key] = CallBudget(limit)
    return _shared_budgets[key]
