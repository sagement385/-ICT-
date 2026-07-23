"""Database-only repository for hospital records."""

from math import cos, radians
from typing import TypeVar

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hospital.geo import distance_km
from app.modules.hospital.models import (
    Hospital,
    HospitalCapability,
    HospitalDepartment,
    HospitalEmergencyProfile,
    HospitalEquipment,
    HospitalRealtimeStatus,
    HospitalSourceIdentity,
)

HospitalChild = TypeVar(
    "HospitalChild",
    HospitalDepartment,
    HospitalEquipment,
    HospitalCapability,
)


class HospitalRepository:
    """Read hospitals without applying clinical filtering rules."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, hospital_id: str) -> Hospital | None:
        """Fetch one hospital by source-backed identifier."""

        return await self.session.get(Hospital, hospital_id)

    async def get_emergency_hospitals_by_ids(
        self,
        hospital_ids: list[str],
    ) -> dict[str, Hospital]:
        """Return active official emergency hospitals keyed by requested ID."""

        if not hospital_ids:
            return {}
        rows = list(
            (
                await self.session.execute(
                    select(Hospital)
                    .join(
                        HospitalEmergencyProfile,
                        HospitalEmergencyProfile.hospital_id == Hospital.hospital_id,
                    )
                    .where(
                        Hospital.hospital_id.in_(hospital_ids),
                        HospitalEmergencyProfile.active.is_(True),
                    )
                )
            ).scalars()
        )
        return {row.hospital_id: row for row in rows}

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

    async def list_source_identity_verifications(
        self,
        hospital_ids: list[str],
    ) -> dict[tuple[str, str, str], bool]:
        """Return explicit review state for source-to-canonical hospital mappings."""

        if not hospital_ids:
            return {}
        rows = list(
            (
                await self.session.execute(
                    select(HospitalSourceIdentity).where(
                        HospitalSourceIdentity.hospital_id.in_(hospital_ids)
                    )
                )
            ).scalars()
        )
        return {
            (row.hospital_id, row.source_name, row.source_record_id): row.verified
            for row in rows
        }

    async def list_departments(
        self,
        hospital_ids: list[str],
    ) -> dict[str, list[HospitalDepartment]]:
        """Return verified department rows grouped by hospital."""

        rows = await self._list_children(HospitalDepartment, hospital_ids)
        grouped: dict[str, list[HospitalDepartment]] = {}
        for row in rows:
            grouped.setdefault(row.hospital_id, []).append(row)
        return grouped

    async def list_equipment(
        self,
        hospital_ids: list[str],
    ) -> dict[str, list[HospitalEquipment]]:
        """Return verified equipment rows grouped by hospital."""

        rows = await self._list_children(HospitalEquipment, hospital_ids)
        grouped: dict[str, list[HospitalEquipment]] = {}
        for row in rows:
            grouped.setdefault(row.hospital_id, []).append(row)
        return grouped

    async def list_capabilities(
        self,
        hospital_ids: list[str],
    ) -> dict[str, list[HospitalCapability]]:
        """Return verified capability rows grouped by hospital."""

        rows = await self._list_children(HospitalCapability, hospital_ids)
        grouped: dict[str, list[HospitalCapability]] = {}
        for row in rows:
            grouped.setdefault(row.hospital_id, []).append(row)
        return grouped

    async def list_latest_realtime_status(
        self,
        hospital_ids: list[str],
    ) -> dict[str, HospitalRealtimeStatus]:
        """Return only the latest trustworthy status snapshot per hospital."""

        if not hospital_ids:
            return {}
        verified_source_updated_at = case(
            (
                HospitalRealtimeStatus.source_timezone != "unknown",
                HospitalRealtimeStatus.source_updated_at,
            ),
            else_=None,
        )
        ranked = (
            select(
                HospitalRealtimeStatus.id.label("status_id"),
                func.row_number()
                .over(
                    partition_by=HospitalRealtimeStatus.hospital_id,
                    order_by=(
                        verified_source_updated_at.desc().nulls_last(),
                        HospitalRealtimeStatus.fetched_at.desc(),
                        HospitalRealtimeStatus.id.desc(),
                    ),
                )
                .label("row_number"),
            )
            .where(HospitalRealtimeStatus.hospital_id.in_(hospital_ids))
            .subquery()
        )
        rows = list(
            (
                await self.session.execute(
                    select(HospitalRealtimeStatus)
                    .join(ranked, HospitalRealtimeStatus.id == ranked.c.status_id)
                    .where(ranked.c.row_number == 1)
                )
            ).scalars()
        )
        return {row.hospital_id: row for row in rows}

    async def _list_children(
        self,
        model: type[HospitalChild],
        hospital_ids: list[str],
    ) -> list[HospitalChild]:
        """Load one normalized child type without N+1 queries."""

        if not hospital_ids:
            return []
        hospital_id = getattr(model, "hospital_id")
        rows = await self.session.execute(
            select(model).where(hospital_id.in_(hospital_ids)).order_by(hospital_id)
        )
        return list(rows.scalars())

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
