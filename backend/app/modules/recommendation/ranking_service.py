"""Final ranking interface with an explicit result boundary."""

import math
from typing import Any

from app.core.errors import ApplicationError


class RankingService:
    """Rank already-calculated results; it does not create a score."""

    def rank(self, results: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        """Return only explicitly scored results in descending score order."""

        eligible = [item for item in results if not bool(item.get("excluded"))]
        for item in eligible:
            score = item.get("total_score")
            if (
                not isinstance(score, (int, float))
                or isinstance(score, bool)
                or not math.isfinite(float(score))
            ):
                raise ApplicationError(
                    code="RECOMMENDATION_SCORE_MISSING",
                    message="순위를 생성할 후보에 유효한 total_score가 없습니다.",
                    details={"hospital_id": item.get("hospital_id")},
                )
        ranked = sorted(
            eligible,
            key=lambda item: (-float(item["total_score"]), str(item.get("hospital_id", ""))),
        )
        return [dict(item, rank=index) for index, item in enumerate(ranked[:limit], start=1)]
