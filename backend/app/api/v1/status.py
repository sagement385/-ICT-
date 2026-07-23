"""Operational readiness endpoints for the live dashboard."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.system.schemas import DataSourceStatusResponse, SystemStatusResponse
from app.modules.system.service import SystemStatusService

router = APIRouter(tags=["status"])


@router.get("/status", response_model=SystemStatusResponse)
async def system_status(
    session: AsyncSession = Depends(get_db_session),
) -> SystemStatusResponse:
    """Return database-backed readiness without probing billable APIs."""

    return await SystemStatusService(session).get_status()


@router.get("/data-sources", response_model=list[DataSourceStatusResponse])
async def data_sources(
    session: AsyncSession = Depends(get_db_session),
) -> list[DataSourceStatusResponse]:
    """Return synchronization state without exposing credentials or raw payloads."""

    return await SystemStatusService(session).list_data_sources()
