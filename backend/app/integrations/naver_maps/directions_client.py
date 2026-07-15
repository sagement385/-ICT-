"""Naver Directions raw client; it does not guess response fields or score routes."""

from collections.abc import Mapping

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.integrations.common.base_client import BaseExternalClient, RawExternalResponse


class NaverDirectionsClient(BaseExternalClient):
    """Fetch raw Directions data after client credentials are configured."""

    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        super().__init__(
            base_url=base_url,
            api_key=settings.naver_map_client_secret,
            source_name="naver-directions",
        )
        self.client_id = settings.naver_map_client_id

    async def fetch_raw(
        self,
        path: str,
        params: Mapping[str, str | int | float],
    ) -> RawExternalResponse:
        """Fetch raw route data; exact auth headers remain a deployment TODO."""

        if not self.client_id:
            raise ApplicationError(
                code="EXTERNAL_SERVICE_NOT_CONFIGURED",
                message="NAVER_MAP_CLIENT_ID가 설정되지 않았습니다.",
                details={"source_name": "naver-directions", "missing_settings": ["NAVER_MAP_CLIENT_ID"]},
            )
        return await self.request("GET", path, params=params, headers={"X-Client-ID": self.client_id})

