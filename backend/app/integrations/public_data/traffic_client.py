"""MOLIT traffic client with no response parser assumptions."""

from collections.abc import Mapping

from app.core.config import get_settings
from app.integrations.common.base_client import BaseExternalClient, RawExternalResponse


class TrafficClient(BaseExternalClient):
    """Fetch raw dataset 15040463 traffic responses."""

    dataset_id = "15040463"

    def __init__(self, base_url: str | None = None) -> None:
        super().__init__(
            base_url=base_url,
            api_key=get_settings().molit_traffic_api_key,
            source_name="molit-traffic",
        )

    async def fetch_raw(
        self,
        path: str,
        params: Mapping[str, str | int | float] | None = None,
    ) -> RawExternalResponse:
        """Fetch raw traffic information."""

        return await self.request("GET", path, params=params)

