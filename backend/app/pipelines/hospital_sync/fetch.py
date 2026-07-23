"""Fetch stage for verified HIRA basic-list pages."""

from app.integrations.common.base_client import RawExternalResponse
from app.integrations.hira.client import HiraClient


async def fetch(
    client: HiraClient,
    page_no: int,
    page_size: int,
    sido_code: str,
) -> RawExternalResponse:
    """Fetch one raw page without parsing provider fields."""

    return await client.fetch_basic_page(page_no, page_size, sido_code)
