"""HIRA clients using the verified hospital-information endpoints."""

from collections.abc import Mapping

from app.core.config import get_settings
from app.integrations.common.base_client import BaseExternalClient, RawExternalResponse


class HiraClient(BaseExternalClient):
    """Fetch raw HIRA responses after credentials and endpoint are configured."""

    detail_endpoints = (
        "getEqpInfo2.8",
        "getSpclDiagInfo2.8",
        "getSpcSbjtSdrInfo2.8",
        "getDgsbjtInfo2.8",
        "getMedOftInfo2.8",
        "getSpclHospAsgFldList2.8",
        "getDtlInfo2.8",
        "getTrnsprtInfo2.8",
        "getNursigGrdInfo2.8",
        "getEtcHstInfo2.8",
    )

    def __init__(
        self,
        base_url: str | None = None,
        base_url_setting_name: str = "HIRA_BASE_URL",
    ) -> None:
        settings = get_settings()
        super().__init__(
            base_url=base_url or settings.hira_base_url,
            api_key=settings.hira_api_key or settings.public_data_api_key,
            source_name="hira",
            api_key_param="ServiceKey",
            base_url_setting_name=base_url_setting_name,
            api_key_setting_names=("HIRA_API_KEY", "PUBLIC_DATA_API_KEY"),
        )

    async def fetch_raw(
        self,
        path: str,
        params: Mapping[str, str | int | float] | None = None,
    ) -> RawExternalResponse:
        """Fetch a provider path without assuming XML/JSON field names."""

        return await self.request("GET", path, params=params)

    async def fetch_basic_page(
        self,
        page_no: int,
        num_of_rows: int,
        sido_code: str,
    ) -> RawExternalResponse:
        """Fetch one verified HIRA basic-list page for Chungbuk or another configured region."""

        return await self.fetch_raw(
            "/getHospBasisList",
            params={
                "pageNo": page_no,
                "numOfRows": num_of_rows,
                "sidoCd": sido_code,
                "_type": "xml",
            },
        )

    async def fetch_detail(
        self,
        endpoint: str,
        ykiho: str,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> RawExternalResponse:
        """Fetch one HIRA detail endpoint for a basic-list ykiho identifier."""

        settings = get_settings()
        detail_client = HiraClient(
            base_url=settings.hira_detail_base_url,
            base_url_setting_name="HIRA_DETAIL_BASE_URL",
        )
        return await detail_client.fetch_raw(
            f"/{endpoint.lstrip('/')}",
            params={"ykiho": ykiho, "pageNo": page_no, "numOfRows": num_of_rows, "_type": "xml"},
        )
