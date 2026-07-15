"""Hospital lookup workflow and freshness mapping."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.hospital.repository import HospitalRepository
from app.modules.hospital.schemas import DataFreshness, HospitalLocation, HospitalResponse
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
        observed_at = hospital.source_updated_at
        freshness_status = "unknown" if observed_at is None else "fresh"
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
                status=freshness_status,
                observed_at=observed_at,
                reason=None if observed_at else "source_updated_at이 없습니다.",
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
        hospitals = await self.repository.list_nearby(latitude, longitude, selected_radius)
        responses: list[HospitalResponse] = []
        for hospital in hospitals:
            response = await self.get(hospital.hospital_id)
            if response is not None:
                responses.append(response)
        return responses
