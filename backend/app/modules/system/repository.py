"""Read-only aggregate queries for operational status."""

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import ScalarSelect

from app.modules.hospital.models import (
    DataSourceRegistry,
    Hospital,
    HospitalCapability,
    HospitalDepartment,
    HospitalEmergencyProfile,
    HospitalEquipment,
    HospitalRealtimeStatus,
    HospitalSourceIdentity,
)
from app.modules.patient.models import PatientCase
from app.modules.recommendation.models import RecommendationPolicy
from app.modules.routing.models import RouteSnapshot
from app.modules.system.schemas import OperationalDataCounts


class SystemStatusRepository:
    """Load registry rows and aggregate coverage without business decisions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_data_sources(self) -> list[DataSourceRegistry]:
        """Return registered sources in stable display order."""

        rows = await self.session.execute(
            select(DataSourceRegistry).order_by(DataSourceRegistry.source_name)
        )
        return list(rows.scalars())

    async def load_counts(self) -> OperationalDataCounts:
        """Return one-query aggregate coverage for the dashboard."""

        active_profiles = HospitalEmergencyProfile.active.is_(True)
        statement = select(
            select(func.count()).select_from(PatientCase).scalar_subquery(),
            select(func.count()).select_from(Hospital).scalar_subquery(),
            select(func.count())
            .select_from(HospitalEmergencyProfile)
            .where(active_profiles)
            .scalar_subquery(),
            select(func.count(distinct(HospitalRealtimeStatus.hospital_id)))
            .select_from(HospitalRealtimeStatus)
            .join(
                HospitalEmergencyProfile,
                HospitalEmergencyProfile.hospital_id == HospitalRealtimeStatus.hospital_id,
            )
            .where(active_profiles)
            .scalar_subquery(),
            self._profile_child_count(HospitalDepartment),
            self._profile_child_count(HospitalEquipment),
            self._profile_child_count(HospitalCapability),
            select(func.count())
            .select_from(HospitalSourceIdentity)
            .where(HospitalSourceIdentity.verified.is_(True))
            .scalar_subquery(),
            select(func.count())
            .select_from(HospitalSourceIdentity)
            .where(HospitalSourceIdentity.verified.is_(False))
            .scalar_subquery(),
            select(func.count()).select_from(RouteSnapshot).scalar_subquery(),
            select(func.count())
            .select_from(RecommendationPolicy)
            .where(RecommendationPolicy.enabled.is_(True))
            .scalar_subquery(),
        )
        row = (await self.session.execute(statement)).one()
        return OperationalDataCounts(
            patients=int(row[0] or 0),
            hospitals=int(row[1] or 0),
            emergency_institutions=int(row[2] or 0),
            emergency_institutions_with_realtime=int(row[3] or 0),
            emergency_institutions_with_departments=int(row[4] or 0),
            emergency_institutions_with_equipment=int(row[5] or 0),
            emergency_institutions_with_capabilities=int(row[6] or 0),
            source_identities_verified=int(row[7] or 0),
            source_identities_unverified=int(row[8] or 0),
            route_snapshots=int(row[9] or 0),
            active_policies=int(row[10] or 0),
        )

    @staticmethod
    def _profile_child_count(child_model: type[object]) -> ScalarSelect[int]:
        """Build a distinct active-profile coverage subquery for a child table."""

        hospital_id = getattr(child_model, "hospital_id")
        return (
            select(func.count(distinct(hospital_id)))
            .select_from(child_model)
            .join(
                HospitalEmergencyProfile,
                HospitalEmergencyProfile.hospital_id == hospital_id,
            )
            .where(HospitalEmergencyProfile.active.is_(True))
            .scalar_subquery()
        )
