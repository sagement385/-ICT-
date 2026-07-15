"""Policy-weighted score interface without hard-coded formulas."""

from typing import Any

from app.core.errors import ApplicationError


class ScoreCalculator:
    """Calculate scores from policy-provided weights after approval."""

    def calculate(
        self,
        features: dict[str, dict[str, Any]],
        weights: dict[str, float],
    ) -> dict[str, dict[str, Any]]:
        """Fail closed instead of applying an arbitrary formula."""

        del features, weights
        raise ApplicationError(
            code="RECOMMENDATION_SCORING_NOT_IMPLEMENTED",
            message="승인된 추천 점수 공식이 아직 없습니다.",
            details={},
        )

