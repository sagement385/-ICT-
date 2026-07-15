"""Database-only repository for hospital records."""

from math import cos, radians

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hospital.geo import distance_km
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

    async def list_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
    ) -> list[Hospital]:
        """Return source-backed hospitals within a coordinate bounding box."""

        latitude_delta = radius_km / 111.0
        longitude_delta = radius_km / max(111.0 * cos(radians(latitude)), 1.0)
        statement = select(Hospital).where(
            Hospital.latitude.is_not(None),
            Hospital.longitude.is_not(None),
            Hospital.latitude.between(latitude - latitude_delta, latitude + latitude_delta),
            Hospital.longitude.between(longitude - longitude_delta, longitude + longitude_delta),
        )
        result = await self.session.execute(statement)
        candidates = list(result.scalars())
        nearby = [
            hospital
            for hospital in candidates
            if hospital.latitude is not None
            and hospital.longitude is not None
            and distance_km(latitude, longitude, hospital.latitude, hospital.longitude) <= radius_km
        ]
        return sorted(
            nearby,
            key=lambda hospital: distance_km(
                latitude,
                longitude,
                hospital.latitude or latitude,
                hospital.longitude or longitude,
            ),
        )
