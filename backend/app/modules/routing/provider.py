"""Routing provider interface for real travel-time data."""

from typing import Protocol

from app.core.errors import ApplicationError
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

