"""Routing workflow around an injected provider."""

from app.modules.routing.provider import RoutingProvider
from app.modules.routing.schemas import RouteQuery, RouteSnapshotData


class RoutingService:
    """Delegate route lookup and preserve provider freshness."""

    def __init__(self, provider: RoutingProvider) -> None:
        self.provider = provider

    async def get_route(self, query: RouteQuery) -> RouteSnapshotData:
        """Fetch one provider route without fallback distance or duration."""

        return await self.provider.get_route(query)

