"""Database-only repository for patient cases."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.patient.models import PatientCase, PatientSymptom


class PatientRepository:
    """Read and write patient records without business decisions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_case(self, incident_id: str) -> tuple[PatientCase, list[PatientSymptom]] | None:
        """Fetch a case and its symptoms by incident id."""

        case = await self.session.get(PatientCase, incident_id)
        if case is None:
            return None
        result = await self.session.execute(
            select(PatientSymptom).where(PatientSymptom.incident_id == incident_id)
        )
        return case, list(result.scalars())

    async def add_case(self, case: PatientCase, symptoms: list[PatientSymptom]) -> None:
        """Persist a patient case and its symptoms in the current transaction."""

        self.session.add(case)
        self.session.add_all(symptoms)
        await self.session.flush()

