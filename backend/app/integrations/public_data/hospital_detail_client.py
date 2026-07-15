"""Public hospital detail client with no response parser assumptions."""

from collections.abc import Mapping

from app.core.config import get_settings
from app.integrations.common.base_client import BaseExternalClient, RawExternalResponse


class HospitalDetailClient(BaseExternalClient):
    """Fetch raw dataset 15001699 responses after endpoint verification."""

    dataset_id = "15001699"

    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        super().__init__(
            base_url=base_url or settings.hira_detail_base_url,
            api_key=settings.public_data_api_key or settings.hira_api_key,
            source_name="public-data-hospital-detail",
            api_key_param="ServiceKey",
        )

    async def fetch_raw(
        self,
        path: str,
        params: Mapping[str, str | int | float] | None = None,
    ) -> RawExternalResponse:
        """Fetch raw hospital detail information."""

        return await self.request("GET", path, params=params)
