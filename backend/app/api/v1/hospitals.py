"""Hospital lookup endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.errors import ApplicationError
from app.modules.hospital.schemas import HospitalResponse
from app.modules.hospital.service import HospitalService

router = APIRouter(prefix="/hospitals", tags=["hospitals"])


@router.get("", response_model=list[HospitalResponse])
async def list_nearby_hospitals(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    radius_km: float = Query(default=10.0, ge=5.0, le=10.0),
    session: AsyncSession = Depends(get_db_session),
) -> list[HospitalResponse]:
    """Return nearby source-backed hospitals for map display, without ranking."""

    return await HospitalService(session).list_nearby(latitude, longitude, radius_km)


@router.get("/{hospital_id}", response_model=HospitalResponse)
async def get_hospital(
    hospital_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> HospitalResponse:
    """Return one source-backed hospital record."""

    hospital = await HospitalService(session).get(hospital_id)
    if hospital is None:
        raise ApplicationError(
            code="HOSPITAL_NOT_FOUND",
            message="해당 hospital_id의 병원 정보가 없습니다.",
            status_code=404,
            details={"hospital_id": hospital_id},
        )
    return hospital
