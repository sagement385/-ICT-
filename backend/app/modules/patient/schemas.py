"""Pydantic schemas matching the patient-event contract."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PatientLocation(BaseModel):
    """Incident location; coordinates may be unknown but must be paired."""

    model_config = ConfigDict(extra="forbid")

    latitude: float | None = Field(ge=-90, le=90)
    longitude: float | None = Field(ge=-180, le=180)
    address_text: str | None

    @model_validator(mode="after")
    def coordinates_are_paired(self) -> "PatientLocation":
        """Prevent a half coordinate pair from entering the database."""

        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude와 longitude는 함께 제공되거나 함께 비어야 합니다.")
        return self


class PatientSymptomInput(BaseModel):
    """One symptom extracted from speech."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    label: str = Field(min_length=1)
    confidence: float | None = Field(ge=0, le=1)


class PatientEventSource(BaseModel):
    """Model provenance for a patient event."""

    model_config = ConfigDict(extra="forbid")

    model_name: str = Field(min_length=1)
    model_version: str = Field(min_length=1)


class PatientEventRequest(BaseModel):
    """Inbound patient event from speech-ai or an approved upstream producer."""

    model_config = ConfigDict(extra="forbid")

    incident_id: str = Field(min_length=1)
    observed_at: datetime
    location: PatientLocation
    symptoms: list[PatientSymptomInput]
    consciousness_status: str | None
    breathing_status: str | None
    bleeding_status: str | None
    urgency_level: str | None
    source: PatientEventSource


class PatientAssistRequest(BaseModel):
    """Free-text chat input for explicit-fact extraction only."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=4000)


class PatientAssistResponse(BaseModel):
    """Structured chat assistance that always requires human confirmation."""

    model_config = ConfigDict(extra="forbid")

    symptoms: list[PatientSymptomInput]
    consciousness_status: str | None = None
    breathing_status: str | None = None
    bleeding_status: str | None = None
    urgency_level: str | None = None
    location_text: str | None = None
    extracted_by_ai: bool = True
    needs_human_review: bool = True
    confidence: float | None = Field(default=None, ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)
    source: PatientEventSource


class PatientCaseResponse(PatientEventRequest):
    """Stored patient event response."""

    created_at: datetime
    updated_at: datetime
