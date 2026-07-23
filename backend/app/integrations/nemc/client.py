"""Raw client for the National Medical Center emergency API."""

from collections.abc import Mapping

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.integrations.common.base_client import BaseExternalClient, RawExternalResponse


class NemcEmergencyClient(BaseExternalClient):
    """Fetch verified emergency-room status and institution data."""

    realtime_endpoint = "getEmrrmRltmUsefulSckbdInfoInqire"
    basic_endpoint = "getEgytBassInfoInqire"
    emergency_list_endpoint = "getEgytListInfoInqire"

    def __init__(self, base_url: str | None = None) -> None:
        """Create a client using the configured public-data key."""

        settings = get_settings()
        super().__init__(
            base_url=base_url or settings.nemc_base_url,
            api_key=settings.nemc_api_key or settings.public_data_api_key,
            source_name="nemc-emergency-medical",
            api_key_param="serviceKey",
            base_url_setting_name="NEMC_BASE_URL",
            api_key_setting_names=("NEMC_API_KEY", "PUBLIC_DATA_API_KEY"),
        )

    async def fetch_raw(
        self,
        endpoint: str,
        params: Mapping[str, str | int | float] | None = None,
    ) -> RawExternalResponse:
        """Fetch an NMC endpoint and preserve its XML response."""

        return await self.request("GET", f"/{endpoint.lstrip('/')}", params=params)

    async def fetch_realtime_status(
        self,
        page_no: int = 1,
        num_of_rows: int = 100,
        stage1: str | None = None,
        stage2: str | None = None,
    ) -> RawExternalResponse:
        """Fetch the source's realtime useful-bed status endpoint."""

        params: dict[str, str | int] = {"pageNo": page_no, "numOfRows": num_of_rows}
        _add_region_params(params, stage1, stage2)
        return await self.fetch_raw(self.realtime_endpoint, params=params)

    async def fetch_basic_information(
        self,
        page_no: int = 1,
        num_of_rows: int = 100,
        stage1: str | None = None,
        stage2: str | None = None,
    ) -> RawExternalResponse:
        """Fetch emergency institution basic information for source matching."""

        params: dict[str, str | int] = {"pageNo": page_no, "numOfRows": num_of_rows}
        _add_region_params(params, stage1, stage2)
        return await self.fetch_raw(self.basic_endpoint, params=params)

    async def fetch_emergency_institutions(
        self,
        page_no: int = 1,
        num_of_rows: int = 1000,
    ) -> RawExternalResponse:
        """Fetch the verified emergency-institution list without region assumptions."""

        return await self.fetch_raw(
            self.emergency_list_endpoint,
            params={"pageNo": page_no, "numOfRows": num_of_rows},
        )


def _add_region_params(
    params: dict[str, str | int],
    stage1: str | None,
    stage2: str | None,
) -> None:
    """Add the documented region pair or reject an incomplete filter."""

    if stage1 is None and stage2 is None:
        return
    if not stage1 or not stage2:
        raise ApplicationError(
            code="NEMC_REGION_FILTER_INCOMPLETE",
            message="NEMC 지역 조회에는 시도와 시군구가 모두 필요합니다.",
            details={"required_settings": ["STAGE1", "STAGE2"]},
        )
    params["STAGE1"] = stage1
    params["STAGE2"] = stage2
