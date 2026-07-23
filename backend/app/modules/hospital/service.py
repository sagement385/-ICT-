"""Hospital lookup workflow and freshness mapping."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.core.freshness import evaluate_freshness
from app.modules.hospital.models import (
    Hospital,
    HospitalEmergencyProfile,
    HospitalRealtimeStatus,
)
from app.modules.hospital.repository import HospitalRepository
from app.modules.hospital.schemas import (
    DataFreshness,
    EmergencyInstitutionProfileResponse,
    HospitalCandidateResponse,
    HospitalCapabilityResponse,
    HospitalDepartmentResponse,
    HospitalEquipmentResponse,
    HospitalLocation,
    HospitalRealtimeStatusResponse,
    HospitalResponse,
)
from app.modules.hospital.validator import validate_hospital_record
from app.modules.patient.repository import PatientRepository


class HospitalService:
    """Expose stored hospital data without inventing missing fields."""

    def __init__(self, session: AsyncSession) -> None:
        self.repository = HospitalRepository(session)
        self.patient_repository = PatientRepository(session)

    async def get(self, hospital_id: str) -> HospitalResponse | None:
        """Return one hospital response or None."""

        hospital = await self.repository.get(hospital_id)
        if hospital is None:
            return None
        validate_hospital_record(hospital)
        emergency_profile = await self.repository.get_emergency_profile(hospital_id)
        identity_verifications = await self.repository.list_source_identity_verifications(
            [hospital_id]
        )
        return self._to_response(hospital, emergency_profile, identity_verifications)

    def _to_response(
        self,
        hospital: Hospital,
        emergency_profile: HospitalEmergencyProfile | None,
        identity_verifications: dict[tuple[str, str, str], bool],
    ) -> HospitalResponse:
        """Map a loaded hospital and optional profile without another query."""

        validate_hospital_record(hospital)
        observed_at = hospital.source_updated_at
        freshness = evaluate_freshness(
            observed_at,
            get_settings().hospital_data_max_age_seconds,
        )
        return HospitalResponse(
            hospital_id=hospital.hospital_id,
            hospital_name=hospital.hospital_name,
            hospital_type_code=hospital.hospital_type_code,
            location=HospitalLocation(
                latitude=hospital.latitude,
                longitude=hospital.longitude,
                address=hospital.address,
            ),
            phone=hospital.phone,
            source_name=hospital.source_name,
            source_record_id=hospital.source_record_id,
            raw_payload_id=hospital.raw_payload_id,
            schema_version=hospital.schema_version,
            source_updated_at=observed_at,
            freshness=DataFreshness(
                status=freshness.status,
                observed_at=freshness.observed_at,
                reason=freshness.reason,
            ),
            emergency_profile=(
                self._emergency_profile_response(emergency_profile, identity_verifications)
                if emergency_profile is not None
                else None
            ),
        )

    async def list_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_km: float | None = None,
    ) -> list[HospitalResponse]:
        """Return source-backed nearby hospitals without ranking or fabricated scores."""

        selected_radius = radius_km or get_settings().candidate_radius_km
        if not 5.0 <= selected_radius <= 10.0:
            raise ValueError("radius_km must be between 5 and 10")
        if await self.repository.count_emergency_profiles() == 0:
            raise ApplicationError(
                code="EMERGENCY_INSTITUTION_DATA_NOT_SYNCED",
                message="응급의료기관 목록이 아직 동기화되지 않았습니다.",
                details={"required_command": "python scripts/sync_emergency_institutions.py"},
            )
        hospitals = await self.repository.list_nearby(latitude, longitude, selected_radius)
        profiles = await self.repository.list_emergency_profiles(
            [hospital.hospital_id for hospital in hospitals]
        )
        identities = await self.repository.list_source_identity_verifications(
            [hospital.hospital_id for hospital in hospitals]
        )
        return [
            self._to_response(hospital, profiles.get(hospital.hospital_id), identities)
            for hospital in hospitals
        ]

    async def list_nearby_candidates(
        self,
        latitude: float,
        longitude: float,
        radius_km: float | None = None,
    ) -> list[HospitalCandidateResponse]:
        """Return nearby candidates with bulk-loaded details and latest status."""

        selected_radius = radius_km or get_settings().candidate_radius_km
        if not 5.0 <= selected_radius <= 10.0:
            raise ValueError("radius_km must be between 5 and 10")
        if await self.repository.count_emergency_profiles() == 0:
            raise ApplicationError(
                code="EMERGENCY_INSTITUTION_DATA_NOT_SYNCED",
                message="응급의료기관 목록이 아직 동기화되지 않았습니다.",
                details={"required_command": "python scripts/sync_emergency_institutions.py"},
            )
        hospitals = await self.repository.list_nearby(latitude, longitude, selected_radius)
        hospital_ids = [hospital.hospital_id for hospital in hospitals]
        profiles = await self.repository.list_emergency_profiles(hospital_ids)
        identities = await self.repository.list_source_identity_verifications(hospital_ids)
        departments = await self.repository.list_departments(hospital_ids)
        equipment = await self.repository.list_equipment(hospital_ids)
        capabilities = await self.repository.list_capabilities(hospital_ids)
        realtime = await self.repository.list_latest_realtime_status(hospital_ids)
        return [
            HospitalCandidateResponse(
                **self._to_response(
                    hospital,
                    profiles.get(hospital.hospital_id),
                    identities,
                ).model_dump(),
                departments=[
                    HospitalDepartmentResponse(
                        department_code=row.department_code,
                        department_name=row.department_name,
                        specialist_count=row.specialist_count,
                        source_name=row.source_name,
                        source_record_id=row.source_record_id,
                        raw_payload_id=row.raw_payload_id,
                        schema_version=row.schema_version,
                        source_updated_at=row.source_updated_at,
                        fetched_at=row.fetched_at,
                    )
                    for row in departments.get(hospital.hospital_id, [])
                ],
                equipment=[
                    HospitalEquipmentResponse(
                        equipment_code=row.equipment_code,
                        equipment_name=row.equipment_name,
                        equipment_count=row.equipment_count,
                        source_name=row.source_name,
                        source_record_id=row.source_record_id,
                        raw_payload_id=row.raw_payload_id,
                        schema_version=row.schema_version,
                        source_updated_at=row.source_updated_at,
                        fetched_at=row.fetched_at,
                    )
                    for row in equipment.get(hospital.hospital_id, [])
                ],
                capabilities=[
                    HospitalCapabilityResponse(
                        capability_code=row.capability_code,
                        capability_name=row.capability_name,
                        available=row.available,
                        source_name=row.source_name,
                        source_record_id=row.source_record_id,
                        raw_payload_id=row.raw_payload_id,
                        schema_version=row.schema_version,
                        source_updated_at=row.source_updated_at,
                        fetched_at=row.fetched_at,
                    )
                    for row in capabilities.get(hospital.hospital_id, [])
                ],
                realtime_status=self._realtime_response(
                    realtime.get(hospital.hospital_id)
                ),
            )
            for hospital in hospitals
        ]

    async def list_nearby_candidates_for_incident(
        self,
        incident_id: str,
        radius_km: float,
    ) -> list[HospitalCandidateResponse]:
        """Resolve patient coordinates from DB so they do not enter access-log URLs."""

        record = await self.patient_repository.get_case(incident_id)
        if record is None:
            raise ApplicationError(
                code="PATIENT_NOT_FOUND",
                message="해당 incident_id의 환자 정보가 없습니다.",
                status_code=404,
                details={"incident_id": incident_id},
            )
        patient, _ = record
        if patient.latitude is None or patient.longitude is None:
            raise ApplicationError(
                code="PATIENT_LOCATION_REQUIRED",
                message="주변 병원을 조회하려면 저장된 환자 좌표가 필요합니다.",
                details={"incident_id": incident_id},
            )
        return await self.list_nearby_candidates(
            patient.latitude,
            patient.longitude,
            radius_km,
        )

    @staticmethod
    def _emergency_profile_response(
        profile: HospitalEmergencyProfile,
        identity_verifications: dict[tuple[str, str, str], bool],
    ) -> EmergencyInstitutionProfileResponse:
        """Map one official profile while keeping its freshness independent from HIRA."""

        profile_fetched_at = profile.fetched_at
        profile_updated_at = profile.source_updated_at
        observed_at = profile_updated_at or profile_fetched_at
        freshness = evaluate_freshness(
            observed_at,
            get_settings().emergency_institution_data_max_age_seconds,
        )
        return EmergencyInstitutionProfileResponse(
            emergency_type_code=profile.emergency_type_code,
            emergency_type_name=profile.emergency_type_name,
            representative_phone=profile.representative_phone,
            emergency_phone=profile.emergency_phone,
            source_name=profile.source_name,
            source_record_id=profile.source_record_id,
            raw_payload_id=profile.raw_payload_id,
            schema_version=profile.schema_version,
            fetched_at=profile_fetched_at,
            source_updated_at=profile_updated_at,
            match_method=profile.match_method,
            identity_verified=identity_verifications.get(
                (profile.hospital_id, profile.source_name, profile.source_record_id),
                False,
            ),
            coordinate_warning=profile.coordinate_warning,
            freshness=DataFreshness(
                status=freshness.status,
                observed_at=freshness.observed_at,
                reason=freshness.reason,
            ),
        )

    @staticmethod
    def _realtime_response(
        status: HospitalRealtimeStatus | None,
    ) -> HospitalRealtimeStatusResponse | None:
        """Map one latest status while respecting unknown source timezone."""

        if status is None:
            return None
        observed_at = (
            status.source_updated_at
            if status.source_timezone not in {"", "unknown"}
            else status.fetched_at
        )
        freshness = evaluate_freshness(
            observed_at,
            get_settings().hospital_status_max_age_seconds,
        )
        return HospitalRealtimeStatusResponse(
            acceptance_status=status.acceptance_status,
            available_beds=status.available_beds,
            source_name=status.source_name,
            source_record_id=status.source_record_id,
            raw_payload_id=status.raw_payload_id,
            schema_version=status.schema_version,
            source_updated_at=status.source_updated_at,
            source_updated_at_raw=status.source_updated_at_raw,
            source_timezone=status.source_timezone,
            fetched_at=status.fetched_at,
            freshness=DataFreshness(
                status=freshness.status,
                observed_at=freshness.observed_at,
                reason=freshness.reason,
            ),
        )
