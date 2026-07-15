"""Naver Directions client with an optional local safety budget."""

from collections.abc import Mapping

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.integrations.common.base_client import BaseExternalClient, RawExternalResponse
from app.integrations.common.rate_limit import get_shared_budget


class NaverDirectionsClient(BaseExternalClient):
    """Fetch raw Directions data after client credentials are configured."""

    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        super().__init__(
            base_url=base_url or settings.naver_directions_base_url,
            api_key=settings.naver_map_client_secret,
            source_name="naver-directions",
            api_key_param=None,
        )
        self.client_id = settings.naver_map_client_id
        self.budget = get_shared_budget("naver-directions5", settings.naver_directions_max_calls)

    async def fetch_raw(
        self,
        path: str,
        params: Mapping[str, str | int | float],
    ) -> RawExternalResponse:
        """Fetch raw route data using the verified Naver Cloud headers."""

        if not self.client_id or not self.api_key:
            missing_settings = []
            if not self.client_id:
                missing_settings.append("NAVER_MAP_CLIENT_ID")
            if not self.api_key:
                missing_settings.append("NAVER_MAP_CLIENT_SECRET")
            raise ApplicationError(
                code="EXTERNAL_SERVICE_NOT_CONFIGURED",
                message="네이버 Directions API 인증정보가 설정되지 않았습니다.",
                details={"source_name": "naver-directions", "missing_settings": missing_settings},
            )
        await self.budget.reserve()
        return await self.request(
            "GET",
            path,
            params=params,
            headers={
                "x-ncp-apigw-api-key-id": self.client_id,
                "x-ncp-apigw-api-key": self.api_key or "",
            },
        )

    @property
    def calls_used(self) -> int:
        """Return the number of route calls made by this process."""

        return self.budget.used

    @property
    def calls_limit(self) -> int | None:
        """Return the configured local limit, or None when unlimited."""

        return self.budget.limit
