"""Gemini client for constrained, non-diagnostic patient-text extraction."""

import json
from typing import Any

from app.core.config import Settings, get_settings
from app.core.errors import ApplicationError
from app.integrations.common.base_client import BaseExternalClient, RawExternalResponse
from app.integrations.gemini.schemas import GeminiExtraction

SYSTEM_INSTRUCTION = (
    "Extract only facts explicitly stated by the user from an emergency chat. "
    "Do not diagnose, infer a medical condition, assign KTAS or Pre-KTAS, "
    "recommend a hospital, or decide whether a hospital can accept the patient. "
    "Use null when a status or location is not explicitly stated. "
    "Keep symptom labels close to the user's wording. "
    "Return urgency_level only when the user explicitly says Level 1, Level 2, "
    "Level 3, or Level 4."
)

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "symptom_labels": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
        "consciousness_status": {
            "type": "STRING",
            "enum": ["의식 있음", "의식 없음", "확인 불가"],
            "nullable": True,
        },
        "breathing_status": {
            "type": "STRING",
            "enum": ["정상 호흡", "호흡 곤란", "호흡 없음", "확인 불가"],
            "nullable": True,
        },
        "bleeding_status": {
            "type": "STRING",
            "enum": ["출혈 있음", "출혈 없음", "확인 불가"],
            "nullable": True,
        },
        "urgency_level": {
            "type": "STRING",
            "enum": ["Level 1", "Level 2", "Level 3", "Level 4"],
            "nullable": True,
        },
        "location_text": {"type": "STRING", "nullable": True},
    },
    "required": [
        "symptom_labels",
        "consciousness_status",
        "breathing_status",
        "bleeding_status",
        "urgency_level",
        "location_text",
    ],
}


class GeminiClient(BaseExternalClient):
    """Call Gemini generateContent with a JSON response schema."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Create a client from the already-loaded application settings."""

        settings = settings or get_settings()
        super().__init__(
            base_url=settings.gemini_base_url,
            api_key=settings.gemini_api_key,
            source_name="gemini",
            api_key_param=None,
            timeout_seconds=settings.gemini_timeout_seconds,
            base_url_setting_name="GEMINI_BASE_URL",
        )
        self.model = settings.gemini_model

    async def extract_patient_facts(self, text: str) -> GeminiExtraction:
        """Extract explicit facts and validate the model response."""

        response = await self._request_generation(text)
        response_text = self._extract_text(response.payload, response.request_id)
        try:
            return GeminiExtraction.model_validate(json.loads(response_text))
        except (json.JSONDecodeError, ValueError) as error:
            raise ApplicationError(
                code="GEMINI_RESPONSE_FORMAT_INVALID",
                message="Gemini structured response could not be validated.",
                details={"request_id": response.request_id},
            ) from error

    async def _request_generation(self, text: str) -> RawExternalResponse:
        """Send a constrained generateContent request."""

        if not self.api_key:
            raise ApplicationError(
                code="EXTERNAL_SERVICE_NOT_CONFIGURED",
                message="Gemini API key is not configured.",
                details={
                    "source_name": "gemini",
                    "missing_settings": ["GEMINI_API_KEY"],
                },
            )
        body = {
            "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
            "contents": [{"role": "user", "parts": [{"text": text}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseSchema": RESPONSE_SCHEMA,
            },
        }
        try:
            return await self.request(
                "POST",
                f"/models/{self.model}:generateContent",
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json_body=body,
            )
        except ApplicationError as error:
            if error.code == "EXTERNAL_SERVICE_HTTP_ERROR":
                raise ApplicationError(
                    code="GEMINI_API_ERROR",
                    message="Gemini API returned an error.",
                    details={
                        "source_name": "gemini",
                        "status_code": error.details.get("status_code"),
                        "request_id": error.details.get("request_id"),
                    },
                ) from error
            raise

    @staticmethod
    def _extract_text(payload: Any, request_id: str) -> str:
        """Extract candidate text without returning the raw provider payload."""

        try:
            candidates = payload["candidates"]
            parts = candidates[0]["content"]["parts"]
            text = "".join(part["text"] for part in parts if isinstance(part.get("text"), str))
        except (KeyError, IndexError, TypeError) as error:
            raise ApplicationError(
                code="GEMINI_RESPONSE_FORMAT_INVALID",
                message="Gemini response did not contain structured text.",
                details={"request_id": request_id},
            ) from error
        if not text:
            raise ApplicationError(
                code="GEMINI_RESPONSE_FORMAT_INVALID",
                message="Gemini response text was empty.",
                details={"request_id": request_id},
            )
        return text
