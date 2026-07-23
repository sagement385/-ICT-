"""Generic policy-weighted scoring with no embedded medical weights."""

import math
from typing import Any

from app.core.errors import ApplicationError
from app.modules.recommendation.policy_repository import PolicyFactor


class ScoreCalculator:
    """Interpret complete DB factor definitions and retain an audit breakdown."""

    def calculate(
        self,
        features: dict[str, dict[str, Any]],
        weights: dict[str, PolicyFactor],
    ) -> dict[str, dict[str, Any]]:
        """Calculate a generic weighted sum only from policy-provided behavior."""

        if not weights:
            raise ApplicationError(
                code="RECOMMENDATION_POLICY_NOT_CONFIGURED",
                message="추천 계산에 사용할 정책 가중치가 없습니다.",
                details={},
            )

        results: dict[str, dict[str, Any]] = {}
        for hospital_id, candidate in features.items():
            values = candidate.get("values")
            freshness = candidate.get("freshness")
            if not isinstance(values, dict) or not isinstance(freshness, dict):
                raise ApplicationError(
                    code="RECOMMENDATION_FEATURES_INVALID",
                    message="추천 특징값 구조가 올바르지 않습니다.",
                    details={"hospital_id": hospital_id},
                )

            total_score = 0.0
            breakdown: dict[str, Any] = {}
            reasons: list[str] = []
            exclusions: list[str] = []
            warnings = list(candidate.get("warnings") or [])

            for factor_name, factor in weights.items():
                raw_value = values.get(factor.source_field)
                freshness_status = self._freshness_status(factor.source_field, freshness)
                unavailable = raw_value is None or freshness_status in {"unknown", "unavailable"}
                if unavailable:
                    action = self._apply_missing_behavior(
                        factor,
                        hospital_id,
                        warnings,
                        exclusions,
                    )
                    if action == "skip" or exclusions:
                        continue

                if freshness_status == "stale":
                    action = self._apply_stale_behavior(
                        factor,
                        hospital_id,
                        warnings,
                        exclusions,
                    )
                    if action == "skip" or exclusions:
                        continue

                if factor.hard_exclusion and self._matches_exclusion(
                    raw_value,
                    factor.configuration,
                    factor_name,
                ):
                    exclusions.append(factor.explanation or f"POLICY_HARD_EXCLUSION:{factor_name}")
                    continue

                normalized = self._normalize(raw_value, factor)
                contribution = normalized * factor.weight_value
                if not math.isfinite(contribution):
                    raise ApplicationError(
                        code="RECOMMENDATION_SCORING_INVALID",
                        message="추천 점수 계산 결과가 유한한 숫자가 아닙니다.",
                        details={"factor_name": factor_name, "hospital_id": hospital_id},
                    )
                total_score += contribution
                breakdown[factor_name] = {
                    "source_field": factor.source_field,
                    "raw_value": raw_value,
                    "normalized_value": normalized,
                    "weight_value": factor.weight_value,
                    "contribution": contribution,
                    "freshness_status": freshness_status,
                }
                if factor.explanation:
                    reasons.append(factor.explanation)

            result = dict(candidate)
            result.update(
                {
                    "total_score": total_score,
                    "score_breakdown": breakdown,
                    "recommendation_reasons": list(dict.fromkeys(reasons)),
                    "exclusion_reasons": list(dict.fromkeys(exclusions)),
                    "warnings": sorted(set(warnings)),
                    "excluded": bool(exclusions),
                }
            )
            results[hospital_id] = result
        return results

    @staticmethod
    def _freshness_status(source_field: str, freshness: dict[str, Any]) -> str | None:
        """Map a source field to the corresponding freshness domain."""

        if source_field.startswith("route.") or source_field == "freshness.route_age_seconds":
            domain = "route"
        elif source_field.startswith("realtime.") or source_field == "freshness.realtime_age_seconds":
            domain = "realtime"
        else:
            domain = "hospital"
        payload = freshness.get(domain)
        return payload.get("status") if isinstance(payload, dict) else None

    @staticmethod
    def _apply_missing_behavior(
        factor: PolicyFactor,
        hospital_id: str,
        warnings: list[str],
        exclusions: list[str],
    ) -> str:
        """Apply the explicit policy action for unavailable or unknown data."""

        if factor.missing_data_behavior == "fail_run":
            raise ApplicationError(
                code="RECOMMENDATION_REQUIRED_DATA_UNAVAILABLE",
                message="추천 정책의 필수 데이터가 없거나 최신성을 확인할 수 없습니다.",
                details={"factor_name": factor.factor_name, "hospital_id": hospital_id},
            )
        if factor.missing_data_behavior == "exclude_candidate":
            exclusions.append(f"POLICY_DATA_MISSING:{factor.factor_name}")
            return "exclude"
        warnings.append(f"POLICY_FACTOR_DATA_MISSING:{factor.factor_name}")
        return "skip"

    @staticmethod
    def _apply_stale_behavior(
        factor: PolicyFactor,
        hospital_id: str,
        warnings: list[str],
        exclusions: list[str],
    ) -> str:
        """Apply the policy action for a source older than its configured threshold."""

        if factor.stale_data_behavior == "fail_run":
            raise ApplicationError(
                code="RECOMMENDATION_REQUIRED_DATA_STALE",
                message="추천 정책의 필수 데이터가 최신성 기준을 초과했습니다.",
                details={"factor_name": factor.factor_name, "hospital_id": hospital_id},
            )
        if factor.stale_data_behavior == "exclude_candidate":
            exclusions.append(f"POLICY_DATA_STALE:{factor.factor_name}")
            return "exclude"
        if factor.stale_data_behavior == "warn":
            warnings.append(f"POLICY_FACTOR_DATA_STALE:{factor.factor_name}")
        return "continue"

    def _normalize(self, raw_value: Any, factor: PolicyFactor) -> float:
        """Normalize a verified raw value using only policy configuration."""

        if factor.normalization == "categorical_map":
            value_map = factor.configuration["value_map"]
            mapped = value_map.get(str(raw_value))
            if not isinstance(mapped, (int, float)) or isinstance(mapped, bool):
                raise ApplicationError(
                    code="RECOMMENDATION_POLICY_DATA_UNMAPPED",
                    message="추천 정책에 원본 범주 값의 매핑이 없습니다.",
                    details={"factor_name": factor.factor_name},
                )
            normalized = float(mapped)
        elif factor.normalization == "boolean":
            if not isinstance(raw_value, bool):
                raise ApplicationError(
                    code="RECOMMENDATION_FEATURE_TYPE_INVALID",
                    message="boolean 정책 factor의 원본 값이 boolean이 아닙니다.",
                    details={"factor_name": factor.factor_name},
                )
            normalized = 1.0 if raw_value else 0.0
        else:
            if (
                not isinstance(raw_value, (int, float))
                or isinstance(raw_value, bool)
                or not math.isfinite(float(raw_value))
            ):
                raise ApplicationError(
                    code="RECOMMENDATION_FEATURE_TYPE_INVALID",
                    message="숫자 정책 factor의 원본 값이 유한한 숫자가 아닙니다.",
                    details={"factor_name": factor.factor_name},
                )
            numeric_value = float(raw_value)
            if factor.normalization == "min_max":
                minimum = float(factor.configuration["minimum"])
                maximum = float(factor.configuration["maximum"])
                normalized = min(max((numeric_value - minimum) / (maximum - minimum), 0.0), 1.0)
            else:
                normalized = numeric_value

        return -normalized if factor.direction == "lower_is_better" else normalized

    @staticmethod
    def _matches_exclusion(
        raw_value: Any,
        configuration: dict[str, Any],
        factor_name: str,
    ) -> bool:
        """Evaluate one policy-provided generic comparison expression."""

        condition = configuration.get("exclude_if")
        if not isinstance(condition, dict):
            return False
        operator = condition.get("operator")
        expected = condition.get("value")
        try:
            if operator == "eq":
                return bool(raw_value == expected)
            if operator == "neq":
                return bool(raw_value != expected)
            if operator == "lt":
                return bool(raw_value < expected)
            if operator == "lte":
                return bool(raw_value <= expected)
            if operator == "gt":
                return bool(raw_value > expected)
            if operator == "gte":
                return bool(raw_value >= expected)
            if operator == "in" and isinstance(expected, list):
                return raw_value in expected
            if operator == "not_in" and isinstance(expected, list):
                return raw_value not in expected
        except TypeError as exc:
            raise ApplicationError(
                code="RECOMMENDATION_POLICY_INVALID",
                message="추천 정책의 제외 조건과 원본 값 형식이 호환되지 않습니다.",
                details={"factor_name": factor_name},
            ) from exc
        raise ApplicationError(
            code="RECOMMENDATION_POLICY_INVALID",
            message="추천 정책의 제외 조건 연산자가 지원되지 않습니다.",
            details={"factor_name": factor_name},
        )
