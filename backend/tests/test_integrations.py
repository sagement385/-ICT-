"""External integration configuration tests."""

import pytest

from app.core.errors import ApplicationError
from app.integrations.hira.client import HiraClient


@pytest.mark.asyncio
async def test_external_client_requires_configuration() -> None:
    """No external response is fabricated when the key or endpoint is absent."""

    client = HiraClient(base_url=None)
    with pytest.raises(ApplicationError) as error:
        await client.fetch_raw("/unconfigured")
    assert error.value.code == "EXTERNAL_SERVICE_NOT_CONFIGURED"

