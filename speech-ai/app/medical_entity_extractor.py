"""Medical entity extraction interface with no clinical defaults."""

from typing import Protocol

from app.errors import SpeechProviderNotConfigured
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
        raise SpeechProviderNotConfigured(["SPEECH_ENTITY_EXTRACTOR"])
