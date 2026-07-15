"""Recommendation policy configuration tests."""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.errors import ApplicationError
from app.modules.recommendation.models import RecommendationPolicy
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


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [False, True])
async def test_disabled_policy_and_policy_without_weights_fail_closed(enabled: bool) -> None:
    """A disabled policy is ignored and an active policy without weights cannot run."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        session.add(
            RecommendationPolicy(
                policy_name="TEST_POLICY_NO_WEIGHTS",
                policy_version="TEST_VERSION_001",
                enabled=enabled,
                evidence_source="TEST_EVIDENCE",
            )
        )
        await session.commit()

        with pytest.raises(ApplicationError) as error:
            await RecommendationPolicyRepository(session).get_active_policy()

        assert error.value.code == "RECOMMENDATION_POLICY_NOT_CONFIGURED"

    await engine.dispose()
