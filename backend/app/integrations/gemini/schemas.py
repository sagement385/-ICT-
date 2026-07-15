"""Provider-neutral schemas for Gemini structured extraction."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GeminiExtraction(BaseModel):
    """Facts explicitly expressed in a chat message, not a medical diagnosis."""

    model_config = ConfigDict(extra="forbid")

    symptom_labels: list[str] = Field(default_factory=list, max_length=10)
    consciousness_status: Literal["의식 있음", "의식 없음", "확인 불가"] | None = None
    breathing_status: Literal["정상 호흡", "호흡 곤란", "호흡 없음", "확인 불가"] | None = None
    bleeding_status: Literal["출혈 있음", "출혈 없음", "확인 불가"] | None = None
    urgency_level: Literal["Level 1", "Level 2", "Level 3", "Level 4"] | None = None
    location_text: str | None = None

