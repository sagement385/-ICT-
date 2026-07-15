"""Routing providers for real travel-time data."""

from typing import Any, Protocol

from app.core.errors import ApplicationError
from app.integrations.naver_maps.directions_client import NaverDirectionsClient
from app.modules.routing.schemas import RouteQuery, RouteSnapshotData


class RoutingProvider(Protocol):
    """Provider contract used by recommendation orchestration."""

    async def get_route(self, query: RouteQuery) -> RouteSnapshotData:
        """Return a source-backed route snapshot."""


class NotConfiguredRoutingProvider:
    """Explicit provider that never fabricates distance or duration."""

    async def get_route(self, query: RouteQuery) -> RouteSnapshotData:
        """Raise a 503-compatible configuration error."""

        del query
        raise ApplicationError(
            code="ROUTE_DATA_UNAVAILABLE",
            message="실제 이동시간 제공자가 설정되지 않았습니다.",
            details={"missing_settings": ["NAVER_MAP_CLIENT_ID", "NAVER_MAP_CLIENT_SECRET"]},
        )


class NaverRoutingProvider:
    """Parse only documented Naver Directions summary fields."""

    def __init__(self, client: NaverDirectionsClient | None = None) -> None:
        """Create a provider with a shared process-local test budget."""

        self.client = client or NaverDirectionsClient()

    async def get_route(self, query: RouteQuery) -> RouteSnapshotData:
        """Fetch and normalize one real route response."""

        raw = await self.client.fetch_raw(
            "/driving",
            params={
                "start": f"{query.origin_longitude},{query.origin_latitude}",
                "goal": f"{query.destination_longitude},{query.destination_latitude}",
                "option": "traoptimal",
            },
        )
        payload = raw.payload
        if not isinstance(payload, dict):
            raise ApplicationError(
                code="ROUTE_RESPONSE_FORMAT_INVALID",
                message="네이버 Directions 응답이 JSON 객체가 아닙니다.",
                details={"request_id": raw.request_id},
            )
        provider_code = payload.get("code")
        if provider_code != 0:
            raise ApplicationError(
                code="ROUTE_PROVIDER_ERROR",
                message=str(payload.get("message") or "네이버 Directions 경로 조회에 실패했습니다."),
                details={"provider_code": provider_code, "request_id": raw.request_id},
            )
        route = self._optimal_route(payload)
        summary = self._summary(route)
        return RouteSnapshotData(
            provider_name="naver-directions5",
            distance_meters=self._int_field(summary, "distance"),
            duration_seconds=round(self._int_field(summary, "duration") / 1000),
            traffic_summary="real-time-provider-response",
            fetched_at=raw.fetched_at,
            path=self._path(route),
        )

    @property
    def calls_used(self) -> int:
        """Expose the process-local test usage for the UI status endpoint."""

        return self.client.calls_used

    @property
    def calls_limit(self) -> int | None:
        """Expose the local limit, or None when route calls are unlimited."""

        return self.client.calls_limit

    @staticmethod
    def _optimal_route(payload: dict[str, Any]) -> dict[str, Any]:
        """Select the documented traffic-optimal route without fallback data."""

        route_container = payload.get("route")
        if not isinstance(route_container, dict):
            raise ApplicationError(
                code="ROUTE_RESPONSE_SCHEMA_INVALID",
                message="네이버 Directions 응답에 route가 없습니다.",
                details={},
            )
        routes = route_container.get("traoptimal")
        if not isinstance(routes, list) or not routes or not isinstance(routes[0], dict):
            raise ApplicationError(
                code="ROUTE_RESPONSE_SCHEMA_INVALID",
                message="네이버 Directions 응답에 traoptimal 경로가 없습니다.",
                details={},
            )
        return routes[0]

    @staticmethod
    def _summary(route: dict[str, Any]) -> dict[str, Any]:
        """Select the documented route summary fields."""

        summary = route.get("summary")
        if not isinstance(summary, dict):
            raise ApplicationError(
                code="ROUTE_RESPONSE_SCHEMA_INVALID",
                message="네이버 Directions 응답에 경로 요약이 없습니다.",
                details={},
            )
        return summary

    @staticmethod
    def _path(route: dict[str, Any]) -> list[tuple[float, float]] | None:
        """Preserve a documented [longitude, latitude] path when present."""

        raw_path = route.get("path")
        if raw_path is None:
            return None
        if not isinstance(raw_path, list):
            raise ApplicationError(
                code="ROUTE_RESPONSE_SCHEMA_INVALID",
                message="Naver Directions 응답의 path 필드가 올바르지 않습니다.",
                details={},
            )
        path: list[tuple[float, float]] = []
        for point in raw_path:
            if (
                not isinstance(point, list)
                or len(point) != 2
                or not all(isinstance(value, (int, float)) for value in point)
            ):
                raise ApplicationError(
                    code="ROUTE_RESPONSE_SCHEMA_INVALID",
                    message="Naver Directions 응답의 path 좌표가 올바르지 않습니다.",
                    details={},
                )
            path.append((float(point[0]), float(point[1])))
        return path

    @staticmethod
    def _int_field(payload: dict[str, Any], field_name: str) -> int:
        """Read a documented numeric summary field."""

        value = payload.get(field_name)
        if not isinstance(value, (int, float)) or value < 0:
            raise ApplicationError(
                code="ROUTE_RESPONSE_SCHEMA_INVALID",
                message=f"네이버 Directions 응답의 {field_name} 필드가 올바르지 않습니다.",
                details={},
            )
        return int(value)
