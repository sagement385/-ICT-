"""Public hospital information client with no response parser assumptions."""

from collections.abc import Mapping

from app.core.config import get_settings
from app.integrations.common.base_client import BaseExternalClient, RawExternalResponse


class HospitalInfoClient(BaseExternalClient):
    """Fetch raw dataset 15001698 responses after endpoint verification."""

    dataset_id = "15001698"

    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        super().__init__(
            base_url=base_url or settings.hira_base_url,
            api_key=settings.public_data_api_key or settings.hira_api_key,
            source_name="public-data-hospital-info",
            api_key_param="ServiceKey",
        )

    async def fetch_raw(
        self,
        path: str,
        params: Mapping[str, str | int | float] | None = None,
    ) -> RawExternalResponse:
        """Fetch raw hospital information."""

        return await self.request("GET", path, params=params)
