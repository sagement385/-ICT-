"""HIRA raw client; endpoint and response fields remain provider-configured."""

from collections.abc import Mapping

from app.core.config import get_settings
from app.integrations.common.base_client import BaseExternalClient, RawExternalResponse


class HiraClient(BaseExternalClient):
    """Fetch raw HIRA responses after credentials and endpoint are configured."""

    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        super().__init__(
            base_url=base_url,
            api_key=settings.hira_api_key,
            source_name="hira",
        )

    async def fetch_raw(
        self,
        path: str,
        params: Mapping[str, str | int | float] | None = None,
    ) -> RawExternalResponse:
        """Fetch a provider path without assuming XML/JSON field names."""

        return await self.request("GET", path, params=params)

