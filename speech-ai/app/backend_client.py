"""HTTP client for submitting a patient-event contract to the backend."""

from typing import Any

import httpx

from app.schemas import PatientEvent


class BackendClient:
    """Submit only validated events to a configured backend URL."""

    def __init__(self, base_url: str | None, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    async def submit_patient_event(self, event: PatientEvent) -> dict[str, Any]:
        """Post an event or fail clearly when the backend is not configured."""

        if not self.base_url:
            raise RuntimeError("BACKEND_API_BASE_URL이 설정되지 않았습니다.")
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.base_url.rstrip('/')}/api/v1/patients", json=event.model_dump(mode="json"))
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise RuntimeError("백엔드 응답이 객체가 아닙니다.")
            return payload

