"""Database-only repository for hospital records."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hospital.models import Hospital


class HospitalRepository:
    """Read hospitals without applying clinical filtering rules."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, hospital_id: str) -> Hospital | None:
        """Fetch one hospital by source-backed identifier."""

        return await self.session.get(Hospital, hospital_id)

    async def list_all(self) -> list[Hospital]:
        """Fetch all normalized hospitals; no ordering implies a recommendation."""

        result = await self.session.execute(select(Hospital))
        return list(result.scalars())

