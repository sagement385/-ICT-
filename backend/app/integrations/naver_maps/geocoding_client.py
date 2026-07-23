"""Naver Geocoding client for address-backed chat intake."""

from collections.abc import Mapping

import httpx

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.integrations.common.base_client import BaseExternalClient, RawExternalResponse


class NaverGeocodingClient(BaseExternalClient):
    """Fetch raw address-to-coordinate responses from Naver Maps."""

    def __init__(
        self,
        base_url: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Create a client using the configured Naver Cloud credentials."""

        settings = get_settings()
        super().__init__(
            base_url=base_url or settings.naver_geocoding_base_url,
            api_key=settings.naver_map_client_secret,
            source_name="naver-geocoding",
            api_key_param=None,
            base_url_setting_name="NAVER_GEOCODING_BASE_URL",
            http_client=http_client,
        )
        self.client_id = settings.naver_map_client_id

    async def fetch_raw(self, query: str) -> RawExternalResponse:
        """Fetch one address query without inventing coordinates."""

        if not self.client_id or not self.api_key:
            missing_settings = []
            if not self.client_id:
                missing_settings.append("NAVER_MAP_CLIENT_ID")
            if not self.api_key:
                missing_settings.append("NAVER_MAP_CLIENT_SECRET")
            raise ApplicationError(
                code="EXTERNAL_SERVICE_NOT_CONFIGURED",
                message="네이버 주소 변환 API 인증정보가 설정되지 않았습니다.",
                details={"source_name": "naver-geocoding", "missing_settings": missing_settings},
            )
        headers: Mapping[str, str] = {
            "x-ncp-apigw-api-key-id": self.client_id,
            "x-ncp-apigw-api-key": self.api_key,
            "Accept": "application/json",
        }
        return await self.request("GET", "/geocode", params={"query": query}, headers=headers)
