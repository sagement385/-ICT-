"""Recommendation policy configuration tests."""

import pytest

from app.core.errors import ApplicationError
from app.modules.recommendation.policy_repository import RecommendationPolicyRepository


class EmptyResult:
    """Minimal result object for an empty policy query."""

    def scalars(self) -> "EmptyResult":
        """Return itself for the repository's scalar access."""

        return self

    def first(self) -> None:
        """Represent no active policy."""

        return None


class EmptySession:
    """Minimal async session double that returns no policy."""

    async def execute(self, statement: object) -> EmptyResult:
        """Return an empty query result."""

        del statement
        return EmptyResult()


@pytest.mark.asyncio
async def test_policy_missing_returns_explicit_error() -> None:
    """Policy lookup never supplies a default weight."""

    with pytest.raises(ApplicationError) as error:
        await RecommendationPolicyRepository(EmptySession()).get_active_policy()  # type: ignore[arg-type]
    assert error.value.code == "RECOMMENDATION_POLICY_NOT_CONFIGURED"

