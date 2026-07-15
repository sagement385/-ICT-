"""Final ranking interface with an explicit result boundary."""

from typing import Any


class RankingService:
    """Rank already-calculated results; it does not create a score."""

    def rank(self, results: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        """Return only explicitly scored results in descending score order."""

        eligible = [item for item in results if not bool(item.get("excluded"))]
        ranked = sorted(eligible, key=lambda item: float(item["total_score"]), reverse=True)
        return [dict(item, rank=index) for index, item in enumerate(ranked[:limit], start=1)]
