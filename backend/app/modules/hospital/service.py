"""Hospital lookup workflow and freshness mapping."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.core.freshness import evaluate_freshness
from app.modules.hospital.models import HospitalEmergencyProfile
from app.modules.hospital.repository import HospitalRepository
from app.modules.hospital.schemas import (
    DataFreshness,
    EmergencyInstitutionProfileResponse,
    HospitalLocation,
    HospitalResponse,
)
from app.modules.hospital.validator import validate_hospital_record


class HospitalService:
    """Expose stored hospital data without inventing missing fields."""

    def __init__(self, session: AsyncSession) -> None:
        self.repository = HospitalRepository(session)

    async def get(self, hospital_id: str) -> HospitalResponse | None:
        """Return one hospital response or None."""

        hospital = await self.repository.get(hospital_id)
        if hospital is None:
            return None
        validate_hospital_record(hospital)
        emergency_profile = await self.repository.get_emergency_profile(hospital_id)
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
                self._emergency_profile_response(emergency_profile)
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
        responses: list[HospitalResponse] = []
        for hospital in hospitals:
            response = await self.get(hospital.hospital_id)
            if response is not None:
                responses.append(response)
        return responses

    @staticmethod
    def _emergency_profile_response(
        profile: HospitalEmergencyProfile,
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
            coordinate_warning=profile.coordinate_warning,
            freshness=DataFreshness(
                status=freshness.status,
                observed_at=freshness.observed_at,
                reason=freshness.reason,
            ),
        )
