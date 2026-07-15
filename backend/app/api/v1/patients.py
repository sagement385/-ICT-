"""Patient event endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.errors import ApplicationError
from app.modules.patient.assist_service import PatientAssistService
from app.modules.patient.schemas import (
    PatientAssistRequest,
    PatientAssistResponse,
    PatientCaseResponse,
    PatientEventRequest,
)
from app.modules.patient.service import PatientService

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=PatientCaseResponse, status_code=201)
async def create_patient(
    event: PatientEventRequest,
    session: AsyncSession = Depends(get_db_session),
) -> PatientCaseResponse:
    """Store a validated patient event and its raw source envelope."""

    return await PatientService(session).create(event)


@router.post("/assist", response_model=PatientAssistResponse)
async def assist_patient(event: PatientAssistRequest) -> PatientAssistResponse:
    """Extract explicit chat facts; this endpoint never stores or recommends."""

    return await PatientAssistService().assist(event.text)


@router.get("/{incident_id}", response_model=PatientCaseResponse)
async def get_patient(
    incident_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> PatientCaseResponse:
    """Return one patient event by incident id."""

    patient = await PatientService(session).get(incident_id)
    if patient is None:
        raise ApplicationError(
            code="PATIENT_NOT_FOUND",
            message="해당 incident_id의 환자 정보가 없습니다.",
            status_code=404,
            details={"incident_id": incident_id},
        )
    return patient
