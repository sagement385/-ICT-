"""Speech AI-side patient event schema kept independent from backend internals."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Location(BaseModel):
    """Location extracted from speech or an upstream source."""

    model_config = ConfigDict(extra="forbid")

    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    address_text: str | None = None

    @model_validator(mode="after")
    def paired_coordinates(self) -> "Location":
        """Ensure coordinates are not partially populated."""

        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude와 longitude는 함께 제공되어야 합니다.")
        return self


class Symptom(BaseModel):
    """One extracted symptom with optional model confidence."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    label: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0, le=1)


class Source(BaseModel):
    """Model provenance."""

    model_config = ConfigDict(extra="forbid")

    model_name: str = Field(min_length=1)
    model_version: str = Field(min_length=1)


class PatientEvent(BaseModel):
    """Output contract sent to the backend after an approved extractor exists."""

    model_config = ConfigDict(extra="forbid")

    incident_id: str = Field(min_length=1)
    observed_at: datetime
    location: Location
    symptoms: list[Symptom]
    consciousness_status: str | None = None
    breathing_status: str | None = None
    bleeding_status: str | None = None
    urgency_level: str | None = None
    source: Source

