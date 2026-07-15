"""Database repository for active recommendation policies and factor behavior."""

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, NoReturn

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError
from app.modules.recommendation.models import RecommendationPolicy, RecommendationWeight

SUPPORTED_SOURCE_FIELDS = frozenset(
    {
        "route.duration_seconds",
        "route.distance_meters",
        "realtime.available_beds",
        "realtime.acceptance_status",
        "freshness.hospital_age_seconds",
        "freshness.realtime_age_seconds",
        "freshness.route_age_seconds",
    }
)
SUPPORTED_DIRECTIONS = frozenset({"higher_is_better", "lower_is_better"})
SUPPORTED_NORMALIZATIONS = frozenset({"identity", "min_max", "boolean", "categorical_map"})
SUPPORTED_MISSING_BEHAVIORS = frozenset({"fail_run", "exclude_candidate", "ignore_factor"})
SUPPORTED_STALE_BEHAVIORS = frozenset({"fail_run", "exclude_candidate", "warn", "allow"})


@dataclass(frozen=True)
class PolicyFactor:
    """One DB-backed factor with no code-provided medical defaults."""

    factor_name: str
    weight_value: float
    source_field: str
    direction: str
    normalization: str
    required: bool
    missing_data_behavior: str
    stale_data_behavior: str
    hard_exclusion: bool
    explanation: str | None
    configuration: dict[str, Any]


@dataclass(frozen=True)
class PolicyBundle:
    """Policy metadata and its validated DB-provided factors."""

    policy: RecommendationPolicy
    weights: dict[str, PolicyFactor]


class RecommendationPolicyRepository:
    """Read only a complete active policy; never supplies factor defaults."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_policy(self) -> PolicyBundle:
        """Return an active policy or an explicit fail-closed configuration error."""

        now = datetime.now(UTC)
        statement = (
            select(RecommendationPolicy)
            .where(
                RecommendationPolicy.enabled.is_(True),
                or_(
                    RecommendationPolicy.effective_from.is_(None),
                    RecommendationPolicy.effective_from <= now,
                ),
                or_(
                    RecommendationPolicy.effective_to.is_(None),
                    RecommendationPolicy.effective_to >= now,
                ),
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

        weight_rows = list(
            (
                await self.session.execute(
                    select(RecommendationWeight).where(
                        RecommendationWeight.policy_id == policy.id,
                        RecommendationWeight.enabled.is_(True),
                    )
                )
            ).scalars()
        )
        if not weight_rows:
            raise ApplicationError(
                code="RECOMMENDATION_POLICY_NOT_CONFIGURED",
                message="활성 추천 정책에 사용 가능한 가중치가 없습니다.",
                details={"policy_id": policy.id},
            )

        factors: dict[str, PolicyFactor] = {}
        for row in weight_rows:
            if row.factor_name in factors:
                self._invalid(policy.id, row.factor_name, "factor_name이 중복되었습니다.")
            factor = self._to_factor(policy.id, row)
            factors[factor.factor_name] = factor
        return PolicyBundle(policy=policy, weights=factors)

    def _to_factor(self, policy_id: str, row: RecommendationWeight) -> PolicyFactor:
        """Validate all metadata required by the generic scoring engine."""

        if not math.isfinite(row.weight_value):
            self._invalid(policy_id, row.factor_name, "weight_value가 유한한 숫자가 아닙니다.")
        if row.source_field not in SUPPORTED_SOURCE_FIELDS:
            self._invalid(policy_id, row.factor_name, "지원되지 않는 source_field입니다.")
        if row.direction not in SUPPORTED_DIRECTIONS:
            self._invalid(policy_id, row.factor_name, "direction이 없거나 지원되지 않습니다.")
        if row.normalization not in SUPPORTED_NORMALIZATIONS:
            self._invalid(policy_id, row.factor_name, "normalization이 없거나 지원되지 않습니다.")
        if row.missing_data_behavior not in SUPPORTED_MISSING_BEHAVIORS:
            self._invalid(
                policy_id,
                row.factor_name,
                "missing_data_behavior가 없거나 지원되지 않습니다.",
            )
        if row.stale_data_behavior not in SUPPORTED_STALE_BEHAVIORS:
            self._invalid(
                policy_id,
                row.factor_name,
                "stale_data_behavior가 없거나 지원되지 않습니다.",
            )
        if row.required and row.missing_data_behavior == "ignore_factor":
            self._invalid(
                policy_id,
                row.factor_name,
                "required factor는 누락 데이터를 무시하도록 설정할 수 없습니다.",
            )

        configuration = dict(row.configuration_json or {})
        self._validate_configuration(policy_id, row, configuration)
        assert row.source_field is not None
        assert row.direction is not None
        assert row.normalization is not None
        assert row.missing_data_behavior is not None
        assert row.stale_data_behavior is not None
        return PolicyFactor(
            factor_name=row.factor_name,
            weight_value=row.weight_value,
            source_field=row.source_field,
            direction=row.direction,
            normalization=row.normalization,
            required=row.required,
            missing_data_behavior=row.missing_data_behavior,
            stale_data_behavior=row.stale_data_behavior,
            hard_exclusion=row.hard_exclusion,
            explanation=row.explanation,
            configuration=configuration,
        )

    def _validate_configuration(
        self,
        policy_id: str,
        row: RecommendationWeight,
        configuration: dict[str, Any],
    ) -> None:
        """Reject incomplete normalization or exclusion configuration."""

        if row.normalization == "min_max":
            minimum = configuration.get("minimum")
            maximum = configuration.get("maximum")
            if (
                not isinstance(minimum, (int, float))
                or isinstance(minimum, bool)
                or not isinstance(maximum, (int, float))
                or isinstance(maximum, bool)
                or not math.isfinite(float(minimum))
                or not math.isfinite(float(maximum))
                or float(maximum) <= float(minimum)
            ):
                self._invalid(
                    policy_id,
                    row.factor_name,
                    "min_max 정규화에는 maximum > minimum인 유한한 경계값이 필요합니다.",
                )
        if row.normalization == "categorical_map":
            value_map = configuration.get("value_map")
            if not isinstance(value_map, dict) or not value_map:
                self._invalid(
                    policy_id,
                    row.factor_name,
                    "categorical_map 정규화에는 비어 있지 않은 value_map이 필요합니다.",
                )
            if any(
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(float(value))
                for value in value_map.values()
            ):
                self._invalid(
                    policy_id,
                    row.factor_name,
                    "value_map의 모든 점수는 유한한 숫자여야 합니다.",
                )
        if row.hard_exclusion and not isinstance(configuration.get("exclude_if"), dict):
            self._invalid(
                policy_id,
                row.factor_name,
                "hard_exclusion factor에는 exclude_if 조건이 필요합니다.",
            )

    @staticmethod
    def _invalid(policy_id: str, factor_name: str, reason: str) -> NoReturn:
        """Raise a stable error without exposing policy values."""

        raise ApplicationError(
            code="RECOMMENDATION_POLICY_INVALID",
            message="활성 추천 정책의 factor 설정이 불완전합니다.",
            details={
                "policy_id": policy_id,
                "factor_name": factor_name,
                "reason": reason,
            },
        )
