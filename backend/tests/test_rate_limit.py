import pytest

from app.core.errors import ApplicationError
from app.integrations.common.rate_limit import CallBudget


@pytest.mark.asyncio
async def test_call_budget_stops_after_configured_limit() -> None:
    budget = CallBudget(1)
    await budget.reserve()
    with pytest.raises(ApplicationError) as error:
        await budget.reserve()
    assert error.value.code == "ROUTE_API_CALL_LIMIT_REACHED"


@pytest.mark.asyncio
async def test_call_budget_allows_unlimited_when_limit_is_none() -> None:
    """An empty local cap delegates quota enforcement to the provider."""

    budget = CallBudget(None)
    for _ in range(100):
        await budget.reserve()
    assert budget.used == 100
