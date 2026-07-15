"""Hospital lookup endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.errors import ApplicationError
from app.modules.hospital.schemas import HospitalResponse
from app.modules.hospital.service import HospitalService

router = APIRouter(prefix="/hospitals", tags=["hospitals"])


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

