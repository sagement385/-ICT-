"""Patient ingestion and lookup workflow."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.patient.models import PatientCase, PatientSymptom, RawIngestionEvent
from app.modules.patient.repository import PatientRepository
from app.modules.patient.schemas import (
    PatientCaseResponse,
    PatientEventRequest,
    PatientEventSource,
    PatientLocation,
    PatientSymptomInput,
)
from app.modules.patient.validator import validate_patient_event


class PatientService:
    """Coordinate validation, raw event storage, and normalized patient storage."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = PatientRepository(session)

    async def create(self, event: PatientEventRequest) -> PatientCaseResponse:
        """Store an event without transforming its clinical values."""

        validate_patient_event(event)
        now = datetime.now(UTC)
        location = event.location
        case = PatientCase(
            incident_id=event.incident_id,
            consciousness_status=event.consciousness_status,
            breathing_status=event.breathing_status,
            bleeding_status=event.bleeding_status,
            urgency_level=event.urgency_level,
            latitude=location.latitude,
            longitude=location.longitude,
            address_text=location.address_text,
            source_model_name=event.source.model_name,
            source_model_version=event.source.model_version,
            received_at=event.observed_at,
        )
        symptoms = [
            PatientSymptom(
                incident_id=event.incident_id,
                symptom_code=symptom.code,
                symptom_label=symptom.label,
                confidence=symptom.confidence,
            )
            for symptom in event.symptoms
        ]
        raw = RawIngestionEvent(
            source_name="speech-ai",
            source_record_id=event.incident_id,
            payload_json=event.model_dump(mode="json"),
            schema_version="patient-event.v1",
            fetched_at=now,
        )
        self.session.add(raw)
        await self.repository.add_case(case, symptoms)
        await self.session.commit()
        return PatientCaseResponse(
            **event.model_dump(),
            created_at=now,
            updated_at=now,
        )

    async def get(self, incident_id: str) -> PatientCaseResponse | None:
        """Return a stored patient event or None for the API layer."""

        record = await self.repository.get_case(incident_id)
        if record is None:
            return None
        case, symptoms = record
        return PatientCaseResponse(
            incident_id=case.incident_id,
            observed_at=case.received_at,
            location=PatientLocation(
                latitude=case.latitude,
                longitude=case.longitude,
                address_text=case.address_text,
            ),
            symptoms=[
                PatientSymptomInput(
                    code=item.symptom_code,
                    label=item.symptom_label,
                    confidence=item.confidence,
                )
                for item in symptoms
            ],
            consciousness_status=case.consciousness_status,
            breathing_status=case.breathing_status,
            bleeding_status=case.bleeding_status,
            urgency_level=case.urgency_level,
            source=PatientEventSource(
                model_name=case.source_model_name,
                model_version=case.source_model_version,
            ),
            created_at=case.created_at,
            updated_at=case.updated_at,
        )
