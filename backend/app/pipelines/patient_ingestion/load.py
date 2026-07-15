"""Patient loading stage delegated to the patient service."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.patient.schemas import PatientCaseResponse, PatientEventRequest
from app.modules.patient.service import PatientService


async def load(session: AsyncSession, event: PatientEventRequest) -> PatientCaseResponse:
    """Persist the event through the domain service."""

    return await PatientService(session).create(event)

