"""Database-only repository for hospital records."""

from math import cos, radians

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hospital.geo import distance_km
from app.modules.hospital.models import Hospital, HospitalEmergencyProfile


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

    async def list_emergency_hospitals(self) -> list[Hospital]:
        """Return only hospitals linked to an official emergency-institution profile."""

        result = await self.session.execute(
            select(Hospital)
            .join(
                HospitalEmergencyProfile,
                HospitalEmergencyProfile.hospital_id == Hospital.hospital_id,
            )
            .where(HospitalEmergencyProfile.active.is_(True))
        )
        return list(result.scalars().unique())

    async def count_emergency_profiles(self) -> int:
        """Count synchronized official emergency-institution profiles."""

        count = await self.session.scalar(
            select(func.count())
            .select_from(HospitalEmergencyProfile)
            .where(HospitalEmergencyProfile.active.is_(True))
        )
        return int(count or 0)

    async def get_emergency_profile(
        self,
        hospital_id: str,
    ) -> HospitalEmergencyProfile | None:
        """Return the official emergency profile for one canonical hospital."""

        result = await self.session.execute(
            select(HospitalEmergencyProfile).where(
                HospitalEmergencyProfile.hospital_id == hospital_id,
                HospitalEmergencyProfile.active.is_(True),
            )
        )
        return result.scalars().first()

    async def list_emergency_profiles(
        self,
        hospital_ids: list[str],
    ) -> dict[str, HospitalEmergencyProfile]:
        """Return emergency profiles keyed by canonical hospital ID."""

        if not hospital_ids:
            return {}
        rows = list(
            (
                await self.session.execute(
                    select(HospitalEmergencyProfile).where(
                        HospitalEmergencyProfile.hospital_id.in_(hospital_ids),
                        HospitalEmergencyProfile.active.is_(True),
                    )
                )
            ).scalars()
        )
        return {row.hospital_id: row for row in rows}

    async def list_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
    ) -> list[Hospital]:
        """Return source-backed hospitals within a coordinate bounding box."""

        latitude_delta = radius_km / 111.0
        longitude_delta = radius_km / max(111.0 * cos(radians(latitude)), 1.0)
        statement = (
            select(Hospital)
            .join(
                HospitalEmergencyProfile,
                HospitalEmergencyProfile.hospital_id == Hospital.hospital_id,
            )
            .where(
                HospitalEmergencyProfile.active.is_(True),
                Hospital.latitude.is_not(None),
                Hospital.longitude.is_not(None),
                Hospital.latitude.between(
                    latitude - latitude_delta,
                    latitude + latitude_delta,
                ),
                Hospital.longitude.between(
                    longitude - longitude_delta,
                    longitude + longitude_delta,
                ),
            )
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
