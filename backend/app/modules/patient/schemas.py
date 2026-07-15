"""Pydantic schemas matching the patient-event contract."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PatientLocation(BaseModel):
    """Incident location; coordinates may be unknown but must be paired."""

    model_config = ConfigDict(extra="forbid")

    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    address_text: str | None = None

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
    confidence: float | None = Field(default=None, ge=0, le=1)


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
    consciousness_status: str | None = None
    breathing_status: str | None = None
    bleeding_status: str | None = None
    urgency_level: str | None = None
    source: PatientEventSource


class PatientCaseResponse(PatientEventRequest):
    """Stored patient event response."""

    created_at: datetime
    updated_at: datetime

