"""Retrying backend client for validated patient-event submission."""

import asyncio
from typing import Any

import httpx

from app.errors import SpeechServiceError
from app.schemas import PatientEvent


class BackendClient:
    """Submit validated events with bounded retry and incident idempotency."""

    def __init__(
        self,
        base_url: str | None,
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.http_client = http_client

    async def submit_patient_event(self, event: PatientEvent) -> dict[str, Any]:
        """Post an event and resolve a duplicate incident to the stored event."""

        if not self.base_url:
            raise SpeechServiceError(
                "BACKEND_NOT_CONFIGURED",
                "BACKEND_API_BASE_URL이 설정되지 않았습니다.",
                {"missing_settings": ["BACKEND_API_BASE_URL"]},
            )
        if self.http_client is not None:
            return await self._submit(self.http_client, event)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            return await self._submit(client, event)

    async def _submit(
        self,
        client: httpx.AsyncClient,
        event: PatientEvent,
    ) -> dict[str, Any]:
        """Execute bounded transport retries without logging event content."""

        assert self.base_url is not None
        url = f"{self.base_url.rstrip('/')}/api/v1/patients"
        for attempt in range(self.max_retries + 1):
            try:
                response = await client.post(
                    url,
                    json=event.model_dump(mode="json"),
                    headers={"Idempotency-Key": event.incident_id},
                    timeout=self.timeout_seconds,
                )
            except httpx.HTTPError as error:
                if attempt >= self.max_retries:
                    raise SpeechServiceError(
                        "BACKEND_REQUEST_FAILED",
                        "환자 이벤트를 백엔드로 전송하지 못했습니다.",
                    ) from error
                await asyncio.sleep(0.25 * (2**attempt))
                continue
            if response.status_code == 409:
                return await self._load_existing(client, event.incident_id)
            if response.status_code >= 500 and attempt < self.max_retries:
                await asyncio.sleep(0.25 * (2**attempt))
                continue
            if response.is_error:
                raise SpeechServiceError(
                    "BACKEND_REJECTED_EVENT",
                    "백엔드가 환자 이벤트를 거부했습니다.",
                    {"status_code": response.status_code},
                )
            return self._object_payload(response)
        raise AssertionError("backend retry loop must return or raise")

    async def _load_existing(
        self,
        client: httpx.AsyncClient,
        incident_id: str,
    ) -> dict[str, Any]:
        """Return the already stored event after a duplicate POST response."""

        assert self.base_url is not None
        response = await client.get(
            f"{self.base_url.rstrip('/')}/api/v1/patients/{incident_id}",
            timeout=self.timeout_seconds,
        )
        if response.is_error:
            raise SpeechServiceError(
                "BACKEND_IDEMPOTENCY_LOOKUP_FAILED",
                "중복 사건의 기존 저장 결과를 조회하지 못했습니다.",
                {"status_code": response.status_code},
            )
        return self._object_payload(response)

    @staticmethod
    def _object_payload(response: httpx.Response) -> dict[str, Any]:
        """Require a JSON object without exposing provider response text."""

        try:
            payload = response.json()
        except ValueError as error:
            raise SpeechServiceError(
                "BACKEND_RESPONSE_INVALID",
                "백엔드 응답이 유효한 JSON이 아닙니다.",
            ) from error
        if not isinstance(payload, dict):
            raise SpeechServiceError(
                "BACKEND_RESPONSE_INVALID",
                "백엔드 응답이 JSON 객체가 아닙니다.",
            )
        return payload
