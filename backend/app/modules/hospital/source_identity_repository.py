"""Database repository for conservative cross-source hospital identities."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hospital.models import HospitalSourceIdentity


class HospitalSourceIdentityRepository:
    """Persist match candidates without treating automated matches as verified."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_source(
        self,
        source_name: str,
        source_record_id: str,
    ) -> HospitalSourceIdentity | None:
        """Return one identity row by the provider's stable identifier."""

        statement = select(HospitalSourceIdentity).where(
            HospitalSourceIdentity.source_name == source_name,
            HospitalSourceIdentity.source_record_id == source_record_id,
        )
        return (await self.session.execute(statement)).scalars().first()

    async def get_verified(
        self,
        source_name: str,
        source_record_id: str,
    ) -> HospitalSourceIdentity | None:
        """Return only a mapping that has been explicitly verified."""

        statement = select(HospitalSourceIdentity).where(
            HospitalSourceIdentity.source_name == source_name,
            HospitalSourceIdentity.source_record_id == source_record_id,
            HospitalSourceIdentity.verified.is_(True),
        )
        return (await self.session.execute(statement)).scalars().first()

    async def record_candidate(
        self,
        *,
        hospital_id: str,
        source_name: str,
        source_record_id: str,
        source_hospital_name: str | None,
        match_method: str,
        match_confidence: float | None,
    ) -> HospitalSourceIdentity:
        """Upsert an automated candidate while preserving any human verification."""

        if match_confidence is not None and not 0 <= match_confidence <= 1:
            raise ValueError("match_confidence must be between 0 and 1")
        row = await self.get_by_source(source_name, source_record_id)
        if row is None:
            row = HospitalSourceIdentity(
                hospital_id=hospital_id,
                source_name=source_name,
                source_record_id=source_record_id,
                source_hospital_name=source_hospital_name,
                match_method=match_method,
                match_confidence=match_confidence,
                verified=False,
            )
            self.session.add(row)
        elif not row.verified:
            row.hospital_id = hospital_id
            row.source_hospital_name = source_hospital_name
            row.match_method = match_method
            row.match_confidence = match_confidence
        await self.session.flush()
        return row

    async def verify(
        self,
        *,
        source_name: str,
        source_record_id: str,
        hospital_id: str,
    ) -> HospitalSourceIdentity | None:
        """Mark an existing reviewed mapping as verified for a canonical hospital."""

        row = await self.get_by_source(source_name, source_record_id)
        if row is None:
            return None
        row.hospital_id = hospital_id
        row.verified = True
        await self.session.flush()
        return row
