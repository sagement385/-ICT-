"""Medical entity extraction interface with no clinical defaults."""

from typing import Protocol

from app.schemas import PatientEvent


class MedicalEntityExtractor(Protocol):
    """Convert approved transcript output into the patient-event contract."""

    def extract(self, transcript: str, incident_id: str) -> PatientEvent:
        """Return a model-backed event after clinical validation."""


class NotConfiguredMedicalEntityExtractor:
    """Explicit extractor used before a real model is selected."""

    def extract(self, transcript: str, incident_id: str) -> PatientEvent:
        """Stop instead of creating a fake patient state."""

        del transcript, incident_id
        raise RuntimeError("실제 의료 엔터티 추출 모델이 설정되지 않았습니다.")

