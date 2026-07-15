"""Gemini-backed chat assistance with a strict human-review boundary."""

import re

from app.core.config import get_settings
from app.integrations.gemini.client import GeminiClient
from app.modules.patient.schemas import (
    PatientAssistResponse,
    PatientEventSource,
    PatientSymptomInput,
)

_EXPLICIT_LEVEL_PATTERN = re.compile(r"\bLevel\s*([1-4])\b", re.IGNORECASE)


class PatientAssistService:
    """Convert user text into reviewable facts without making clinical decisions."""

    def __init__(self, client: GeminiClient | None = None) -> None:
        """Create the service with an injectable client for deterministic tests."""

        self.client = client or GeminiClient(get_settings())

    async def assist(self, text: str) -> PatientAssistResponse:
        """Extract explicit facts and mark the output for human confirmation."""

        extraction = await self.client.extract_patient_facts(text)
        urgency_level = extraction.urgency_level
        warnings = ["Gemini extraction is advisory and must be confirmed by a responder."]
        if urgency_level and not _EXPLICIT_LEVEL_PATTERN.search(text):
            urgency_level = None
            warnings.append("Urgency was not explicitly stated and was discarded.")

        symptoms = [
            PatientSymptomInput(
                code=f"GEMINI_SYMPTOM_{index}",
                label=label,
                confidence=None,
            )
            for index, label in enumerate(extraction.symptom_labels, start=1)
        ]
        return PatientAssistResponse(
            symptoms=symptoms,
            consciousness_status=extraction.consciousness_status,
            breathing_status=extraction.breathing_status,
            bleeding_status=extraction.bleeding_status,
            urgency_level=urgency_level,
            location_text=extraction.location_text,
            extracted_by_ai=True,
            needs_human_review=True,
            confidence=None,
            warnings=warnings,
            source=PatientEventSource(
                model_name="gemini-chat-extractor",
                model_version=get_settings().gemini_model,
            ),
        )
