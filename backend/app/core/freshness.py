"""Shared timestamp freshness evaluation without optimistic defaults."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Literal

FreshnessStatus = Literal["fresh", "stale", "unknown", "unavailable"]


@dataclass(frozen=True)
class FreshnessEvaluation:
    """Explain how a source timestamp was classified."""

    status: FreshnessStatus
    observed_at: datetime | None
    age_seconds: float | None
    max_age_seconds: int | None
    reason: str | None
    warning_code: str | None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation for audit payloads."""

        payload = asdict(self)
        if self.observed_at is not None:
            payload["observed_at"] = self.observed_at.isoformat()
        return payload


def evaluate_freshness(
    observed_at: datetime | None,
    max_age_seconds: int | None,
    *,
    now: datetime | None = None,
) -> FreshnessEvaluation:
    """Classify a timestamp only when both timestamp and threshold are known."""

    if observed_at is None:
        return FreshnessEvaluation(
            status="unknown",
            observed_at=None,
            age_seconds=None,
            max_age_seconds=max_age_seconds,
            reason="원본 데이터의 기준 시각이 없습니다.",
            warning_code="DATA_TIMESTAMP_UNKNOWN",
        )
    if max_age_seconds is None:
        return FreshnessEvaluation(
            status="unknown",
            observed_at=observed_at,
            age_seconds=None,
            max_age_seconds=None,
            reason="데이터 최신성 임계값이 설정되지 않았습니다.",
            warning_code="FRESHNESS_THRESHOLD_NOT_CONFIGURED",
        )

    reference = now or datetime.now(UTC)
    normalized_observed_at = _as_utc(observed_at)
    normalized_reference = _as_utc(reference)
    age_seconds = (normalized_reference - normalized_observed_at).total_seconds()
    if age_seconds < 0:
        return FreshnessEvaluation(
            status="unknown",
            observed_at=observed_at,
            age_seconds=age_seconds,
            max_age_seconds=max_age_seconds,
            reason="원본 데이터의 기준 시각이 현재보다 미래입니다.",
            warning_code="DATA_TIMESTAMP_INVALID",
        )
    if age_seconds > max_age_seconds:
        return FreshnessEvaluation(
            status="stale",
            observed_at=observed_at,
            age_seconds=age_seconds,
            max_age_seconds=max_age_seconds,
            reason="설정된 데이터 최신성 임계값을 초과했습니다.",
            warning_code="DATA_STALE",
        )
    return FreshnessEvaluation(
        status="fresh",
        observed_at=observed_at,
        age_seconds=age_seconds,
        max_age_seconds=max_age_seconds,
        reason=None,
        warning_code=None,
    )


def unavailable_freshness(reason: str, warning_code: str) -> FreshnessEvaluation:
    """Represent a source that was not available for the current workflow."""

    return FreshnessEvaluation(
        status="unavailable",
        observed_at=None,
        age_seconds=None,
        max_age_seconds=None,
        reason=reason,
        warning_code=warning_code,
    )


def _as_utc(value: datetime) -> datetime:
    """Normalize naive database timestamps as UTC for deterministic comparison."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
