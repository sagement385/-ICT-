"""Routing provider status for the test dashboard."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.integrations.naver_maps.directions_client import NaverDirectionsClient
from app.modules.routing.provider import NaverRoutingProvider
from app.modules.routing.schemas import (
    RouteBatchError,
    RouteBatchItem,
    RouteBatchQuery,
    RouteBatchResponse,
    RouteQuery,
    RouteSnapshotData,
)

router = APIRouter(prefix="/routing", tags=["routing"])


@router.get("/status")
async def routing_status() -> dict[str, object]:
    """Expose configuration and the process-local Directions test budget."""

    settings = get_settings()
    client = NaverDirectionsClient()
    configured = bool(settings.naver_map_client_id and settings.naver_map_client_secret)
    return {
        "provider": "naver-directions5",
        "configured": configured,
        "calls_used": client.calls_used,
        "calls_limit": client.calls_limit,
        "status": "configured" if configured else "not_configured",
    }


@router.post("/test", response_model=RouteSnapshotData)
async def test_route(query: RouteQuery) -> RouteSnapshotData:
    """Fetch one real Naver Directions 5 route for integration verification."""

    return await NaverRoutingProvider().get_route(query)


@router.post("/batch", response_model=RouteBatchResponse)
async def batch_routes(query: RouteBatchQuery) -> RouteBatchResponse:
    """Fetch real routes for visible map destinations without fake fallbacks."""

    provider = NaverRoutingProvider()
    routes: list[RouteBatchItem] = []
    errors: list[RouteBatchError] = []
    for destination in query.destinations:
        route_query = RouteQuery(
            origin_latitude=query.origin_latitude,
            origin_longitude=query.origin_longitude,
            destination_latitude=destination.latitude,
            destination_longitude=destination.longitude,
        )
        try:
            route = await provider.get_route(route_query)
        except ApplicationError as error:
            errors.append(
                RouteBatchError(
                    hospital_id=destination.hospital_id,
                    code=error.code,
                    message=error.message,
                )
            )
            continue
        routes.append(RouteBatchItem(hospital_id=destination.hospital_id, route=route))
    return RouteBatchResponse(routes=routes, errors=errors)
