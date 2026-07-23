"""Configurable async HTTP client that preserves raw response envelopes."""

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from typing import Any
from uuid import uuid4

import httpx

from app.core.errors import ApplicationError
from app.integrations.common.rate_limit import is_rate_limited
from app.integrations.common.retry import exponential_backoff

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RawExternalResponse:
    """Provider response envelope stored before any parser touches it."""

    request_id: str
    status_code: int
    fetched_at: datetime
    headers: Mapping[str, str]
    payload: Any


class BaseExternalClient:
    """HTTP boundary with timeout, bounded retry, and configuration checks."""

    def __init__(
        self,
        base_url: str | None,
        api_key: str | None,
        source_name: str,
        api_key_param: str | None = "serviceKey",
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
        base_url_setting_name: str = "BASE_URL",
        api_key_setting_names: tuple[str, ...] = ("API_KEY",),
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.source_name = source_name
        self.api_key_param = api_key_param
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.base_url_setting_name = base_url_setting_name
        self.api_key_setting_names = api_key_setting_names
        self.http_client = http_client

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str | int | float] | None = None,
        headers: Mapping[str, str] | None = None,
        json_body: Any | None = None,
    ) -> RawExternalResponse:
        """Make an HTTP request and return a raw response without field assumptions."""

        if not self.base_url or (self.api_key_param and not self.api_key):
            raise ApplicationError(
                code="EXTERNAL_SERVICE_NOT_CONFIGURED",
                message=f"{self.source_name} 외부 서비스 설정이 없습니다.",
                details={"source_name": self.source_name, "missing_settings": self._missing_settings()},
            )

        request_id = str(uuid4())
        started_at = monotonic()
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        request_headers = {"X-Request-ID": request_id, **(headers or {})}
        request_params = dict(params or {})
        if self.api_key_param and self.api_key:
            request_params.setdefault(self.api_key_param, self.api_key)
        if self.http_client is not None:
            return await self._request_with_client(
                self.http_client,
                method,
                url,
                request_id,
                request_params,
                request_headers,
                json_body,
                started_at,
            )
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            return await self._request_with_client(
                client,
                method,
                url,
                request_id,
                request_params,
                request_headers,
                json_body,
                started_at,
            )

    async def _request_with_client(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        request_id: str,
        request_params: dict[str, str | int | float],
        request_headers: dict[str, str],
        json_body: Any | None,
        started_at: float,
    ) -> RawExternalResponse:
        """Execute the retry loop using an injected or request-owned HTTP client."""

        logger.info(
            "external_request_started source=%s method=%s request_id=%s",
            self.source_name,
            method,
            request_id,
        )
        for attempt in range(self.max_retries + 1):
            try:
                request_kwargs: dict[str, Any] = {
                    "params": request_params,
                    "headers": request_headers,
                    "timeout": self.timeout_seconds,
                }
                if json_body is not None:
                    request_kwargs["json"] = json_body
                response = await client.request(method, url, **request_kwargs)
            except httpx.HTTPError as exc:
                if attempt >= self.max_retries:
                    logger.warning(
                        "external_request_transport_failed source=%s request_id=%s attempts=%s",
                        self.source_name,
                        request_id,
                        attempt + 1,
                    )
                    raise ApplicationError(
                        code="EXTERNAL_SERVICE_REQUEST_FAILED",
                        message=f"{self.source_name} 요청에 실패했습니다.",
                        details={"source_name": self.source_name, "request_id": request_id},
                    ) from exc
                logger.warning(
                    "external_request_retry source=%s request_id=%s attempt=%s reason=transport",
                    self.source_name,
                    request_id,
                    attempt + 1,
                )
                await asyncio.sleep(exponential_backoff(attempt))
                continue

            if is_rate_limited(response.status_code) and attempt < self.max_retries:
                logger.warning(
                    "external_request_retry source=%s request_id=%s attempt=%s reason=rate_limit",
                    self.source_name,
                    request_id,
                    attempt + 1,
                )
                await asyncio.sleep(exponential_backoff(attempt))
                continue
            if response.is_error:
                logger.warning(
                    "external_request_http_failed source=%s request_id=%s status=%s",
                    self.source_name,
                    request_id,
                    response.status_code,
                )
                raise ApplicationError(
                    code="EXTERNAL_SERVICE_HTTP_ERROR",
                    message=f"{self.source_name} 응답이 HTTP 오류를 반환했습니다.",
                    details={
                        "source_name": self.source_name,
                        "status_code": response.status_code,
                        "request_id": request_id,
                    },
                )
            logger.info(
                "external_request_completed source=%s request_id=%s status=%s elapsed_ms=%s",
                self.source_name,
                request_id,
                response.status_code,
                round((monotonic() - started_at) * 1000),
            )
            return RawExternalResponse(
                request_id=request_id,
                status_code=response.status_code,
                fetched_at=datetime.now(UTC),
                headers=dict(response.headers),
                payload=self._decode_payload(response),
            )
        raise AssertionError("HTTP retry loop must return or raise")

    def _missing_settings(self) -> list[str]:
        """Describe the exact missing environment settings without exposing values."""

        missing: list[str] = []
        if not self.base_url:
            missing.append(self.base_url_setting_name)
        if self.api_key_param and not self.api_key:
            missing.extend(self.api_key_setting_names)
        return missing

    @staticmethod
    def _decode_payload(response: httpx.Response) -> Any:
        """Decode JSON when possible and preserve non-JSON bodies as text."""

        if not response.content:
            return None
        text_payload = response.content.decode("utf-8-sig", errors="replace")
        try:
            import json

            return json.loads(text_payload)
        except ValueError:
            return text_payload
