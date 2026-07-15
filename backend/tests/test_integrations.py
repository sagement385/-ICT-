"""External integration configuration tests."""

from types import SimpleNamespace

import pytest

from app.core.errors import ApplicationError
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
