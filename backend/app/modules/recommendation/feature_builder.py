"""Build source-backed, non-clinical features for policy-controlled scoring."""

from datetime import datetime
from typing import Any

from app.core.config import get_settings
from app.core.freshness import (
    FreshnessEvaluation,
    evaluate_freshness,
    unavailable_freshness,
)
from app.modules.hospital.models import Hospital
from app.modules.patient.schemas import PatientEventRequest
from app.modules.routing.schemas import RouteSnapshotData


class FeatureBuilder:
    """Expose verified source values while leaving their meaning to the policy."""

    def build(
        self,
        patient: PatientEventRequest,
        hospitals: list[Hospital],
        route_data: dict[str, RouteSnapshotData],
        realtime_status: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """Build only technical route, status, and freshness features."""

        del patient
        settings = get_settings()
        features: dict[str, dict[str, Any]] = {}
        for hospital in hospitals:
            route = route_data.get(hospital.hospital_id)
            status = realtime_status.get(hospital.hospital_id)

            hospital_freshness = evaluate_freshness(
                hospital.source_updated_at,
                settings.hospital_data_max_age_seconds,
            )
            route_freshness = (
                evaluate_freshness(route.fetched_at, settings.route_data_max_age_seconds)
                if route is not None
                else unavailable_freshness(
                    "실제 경로 데이터를 조회하지 못했습니다.",
                    "ROUTE_DATA_UNAVAILABLE",
                )
            )
            realtime_observed_at = self._status_observed_at(status)
            realtime_freshness = (
                evaluate_freshness(
                    realtime_observed_at,
                    settings.hospital_status_max_age_seconds,
                )
                if status is not None
                else unavailable_freshness(
                    "병원 실시간 수용 상태를 조회하지 못했습니다.",
                    "HOSPITAL_REALTIME_STATUS_UNAVAILABLE",
                )
            )

            freshness = {
                "hospital": self._freshness_payload(hospital_freshness, "hospital"),
                "realtime": self._freshness_payload(realtime_freshness, "realtime"),
                "route": self._freshness_payload(route_freshness, "route"),
            }
            warnings = sorted(
                {
                    payload["warning_code"]
                    for payload in freshness.values()
                    if payload.get("warning_code")
                }
            )
            features[hospital.hospital_id] = {
                "hospital_id": hospital.hospital_id,
                "hospital_name": hospital.hospital_name,
                "location": {
                    "latitude": hospital.latitude,
                    "longitude": hospital.longitude,
                    "address": hospital.address,
                },
                "values": {
                    "route.duration_seconds": route.duration_seconds if route else None,
                    "route.distance_meters": route.distance_meters if route else None,
                    "realtime.available_beds": status.get("available_beds") if status else None,
                    "realtime.acceptance_status": (
                        status.get("acceptance_status") if status else None
                    ),
                    "freshness.hospital_age_seconds": hospital_freshness.age_seconds,
                    "freshness.realtime_age_seconds": realtime_freshness.age_seconds,
                    "freshness.route_age_seconds": route_freshness.age_seconds,
                },
                "travel_time": route.model_dump(mode="json") if route else None,
                "freshness": freshness,
                "source_provenance": {
                    "hospital": {
                        "source_name": hospital.source_name,
                        "source_record_id": hospital.source_record_id,
                        "raw_payload_id": hospital.raw_payload_id,
                        "schema_version": hospital.schema_version,
                        "source_updated_at": self._iso(hospital.source_updated_at),
                    },
                    "realtime": self._status_provenance(status),
                    "route": (
                        {
                            "source_name": route.source_name,
                            "source_record_id": route.source_record_id,
                            "raw_payload_id": route.raw_payload_id,
                            "schema_version": route.schema_version,
                            "fetched_at": route.fetched_at.isoformat(),
                        }
                        if route
                        else None
                    ),
                },
                "warnings": warnings,
            }
        return features

    @staticmethod
    def _status_observed_at(status: dict[str, Any] | None) -> datetime | None:
        """Prefer a provider update time and fall back to fetch time."""

        if status is None:
            return None
        source_updated_at = status.get("source_updated_at")
        fetched_at = status.get("fetched_at")
        if isinstance(source_updated_at, datetime):
            return source_updated_at
        return fetched_at if isinstance(fetched_at, datetime) else None

    @staticmethod
    def _freshness_payload(
        evaluation: FreshnessEvaluation,
        domain: str,
    ) -> dict[str, Any]:
        """Use domain-specific stale warnings while preserving the explanation."""

        payload = evaluation.to_dict()
        if evaluation.status == "stale":
            payload["warning_code"] = {
                "hospital": "HOSPITAL_DATA_STALE",
                "realtime": "HOSPITAL_REALTIME_STATUS_STALE",
                "route": "ROUTE_DATA_STALE",
            }[domain]
        return payload

    @staticmethod
    def _status_provenance(status: dict[str, Any] | None) -> dict[str, Any] | None:
        """Return only traceability fields from a realtime row."""

        if status is None:
            return None
        return {
            "source_name": status.get("source_name"),
            "source_record_id": status.get("source_record_id"),
            "raw_payload_id": status.get("raw_payload_id"),
            "schema_version": status.get("schema_version"),
            "source_updated_at": FeatureBuilder._iso(status.get("source_updated_at")),
            "fetched_at": FeatureBuilder._iso(status.get("fetched_at")),
        }

    @staticmethod
    def _iso(value: Any) -> str | None:
        """Serialize verified timestamps without coercing unknown values."""

        return value.isoformat() if isinstance(value, datetime) else None
