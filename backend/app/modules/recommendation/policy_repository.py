"""Database repository for active recommendation policies and weights."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError
from app.modules.recommendation.models import RecommendationPolicy, RecommendationWeight


@dataclass(frozen=True)
class PolicyBundle:
    """Policy metadata and its DB-provided factor weights."""

    policy: RecommendationPolicy
    weights: dict[str, float]


class RecommendationPolicyRepository:
    """Read only the active policy; never supplies default weights."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_policy(self) -> PolicyBundle:
        """Return an active policy or the explicit configuration error."""

        now = datetime.now(UTC)
        statement = (
            select(RecommendationPolicy)
            .where(
                RecommendationPolicy.enabled.is_(True),
                or_(RecommendationPolicy.effective_from.is_(None), RecommendationPolicy.effective_from <= now),
                or_(RecommendationPolicy.effective_to.is_(None), RecommendationPolicy.effective_to >= now),
            )
            .order_by(RecommendationPolicy.created_at.desc())
        )
        policy = (await self.session.execute(statement)).scalars().first()
        if policy is None:
            raise ApplicationError(
                code="RECOMMENDATION_POLICY_NOT_CONFIGURED",
                message="활성화된 추천 정책이 없습니다.",
                details={},
            )

        weight_rows = await self.session.execute(
            select(RecommendationWeight).where(RecommendationWeight.policy_id == policy.id)
        )
        weights = {row.factor_name: row.weight_value for row in weight_rows.scalars()}
        if not weights:
            raise ApplicationError(
                code="RECOMMENDATION_POLICY_NOT_CONFIGURED",
                message="활성 추천 정책에 가중치가 없습니다.",
                details={"policy_id": policy.id},
            )
        return PolicyBundle(policy=policy, weights=weights)

