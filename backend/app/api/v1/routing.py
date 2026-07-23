"""Routing API endpoints with service-layer orchestration."""

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.dependencies import get_external_http_client
from app.integrations.naver_maps.directions_client import NaverDirectionsClient
from app.modules.routing.provider import NaverRoutingProvider
from app.modules.routing.schemas import (
    RouteBatchQuery,
    RouteBatchResponse,
    RouteQuery,
    RouteSnapshotData,
)
from app.modules.routing.service import RoutingService

router = APIRouter(prefix="/routing", tags=["routing"])


@router.get("/status")
async def routing_status() -> dict[str, object]:
    """Expose configuration and the process-local Directions safety budget."""

    settings = get_settings()
    client = NaverDirectionsClient()
    configured = bool(settings.naver_map_client_id and settings.naver_map_client_secret)
    return {
        "provider": "naver-directions5",
        "configured": configured,
        "calls_used": client.calls_used,
        "calls_limit": client.calls_limit,
        "cache_max_age_seconds": settings.route_data_max_age_seconds,
        "max_concurrency": settings.routing_max_concurrency,
        "status": "configured" if configured else "not_configured",
    }


@router.post("/test", response_model=RouteSnapshotData)
async def test_route(
    query: RouteQuery,
    http_client: httpx.AsyncClient = Depends(get_external_http_client),
) -> RouteSnapshotData:
    """Fetch one real route for explicit integration diagnostics."""

    return await NaverRoutingProvider(
        NaverDirectionsClient(http_client=http_client)
    ).get_route(query)


@router.post("/batch", response_model=RouteBatchResponse)
async def batch_routes(
    query: RouteBatchQuery,
    session: AsyncSession = Depends(get_db_session),
    http_client: httpx.AsyncClient = Depends(get_external_http_client),
) -> RouteBatchResponse:
    """Return real or explicitly valid cached routes for stored canonical records."""

    return await RoutingService(
        session,
        NaverRoutingProvider(NaverDirectionsClient(http_client=http_client)),
    ).get_batch(query)
