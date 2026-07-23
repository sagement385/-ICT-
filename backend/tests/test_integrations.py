"""External integration configuration tests."""

from types import SimpleNamespace

import httpx
import pytest

from app.core.errors import ApplicationError
from app.integrations.common.base_client import BaseExternalClient
from app.integrations.hira.client import HiraClient


@pytest.mark.asyncio
async def test_external_client_requires_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    """No external response is fabricated when the key or endpoint is absent."""

    monkeypatch.setattr(
        "app.integrations.hira.client.get_settings",
        lambda: SimpleNamespace(
            hira_base_url=None,
            hira_api_key=None,
            public_data_api_key=None,
        ),
    )
    client = HiraClient(base_url=None)
    with pytest.raises(ApplicationError) as error:
        await client.fetch_raw("/unconfigured")
    assert error.value.code == "EXTERNAL_SERVICE_NOT_CONFIGURED"
    assert error.value.details["missing_settings"] == [
        "HIRA_BASE_URL",
        "HIRA_API_KEY",
        "PUBLIC_DATA_API_KEY",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 403, 429, 500])
async def test_external_http_errors_are_not_converted_to_success(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
) -> None:
    """Provider HTTP failures retain status metadata and never fabricate payloads."""

    class StubAsyncClient:
        """Return one controlled provider status without network access."""

        def __init__(self, timeout: float) -> None:
            del timeout

        async def __aenter__(self) -> "StubAsyncClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            del args

        async def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
            del kwargs
            return httpx.Response(status_code, request=httpx.Request(method, url))

    monkeypatch.setattr(
        "app.integrations.common.base_client.httpx.AsyncClient",
        StubAsyncClient,
    )
    client = BaseExternalClient(
        base_url="https://test-provider.invalid",
        api_key="TEST_API_KEY",
        source_name="TEST_PROVIDER",
        max_retries=0,
    )

    with pytest.raises(ApplicationError) as error:
        await client.request("GET", "/status")

    assert error.value.code == "EXTERNAL_SERVICE_HTTP_ERROR"
    assert error.value.details["status_code"] == status_code
    assert "payload" not in error.value.details
