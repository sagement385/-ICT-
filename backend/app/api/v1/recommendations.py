"""Recommendation run and latest-result endpoints."""

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_external_http_client
from app.integrations.naver_maps.directions_client import NaverDirectionsClient
from app.modules.recommendation.recommendation_service import RecommendationService
from app.modules.recommendation.schemas import RecommendationRequest, RecommendationResultResponse
from app.modules.routing.provider import NaverRoutingProvider

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/{incident_id}/run", response_model=RecommendationResultResponse)
async def run_recommendation(
    incident_id: str,
    request: RecommendationRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
    http_client: httpx.AsyncClient = Depends(get_external_http_client),
) -> RecommendationResultResponse:
    """Run only when patient, verified source data, policy, and weights exist."""

    limit = request.limit if request is not None else 3
    return await RecommendationService(
        session,
        route_provider=NaverRoutingProvider(
            NaverDirectionsClient(http_client=http_client)
        ),
    ).run(incident_id, limit)


@router.get("/{incident_id}/latest", response_model=RecommendationResultResponse)
async def get_latest_recommendation(
    incident_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> RecommendationResultResponse:
    """Return a persisted result; never display a fabricated result."""

    return await RecommendationService(session).latest(incident_id)
