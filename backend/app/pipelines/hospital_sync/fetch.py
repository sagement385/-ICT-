"""Fetch stage for raw source responses."""

from app.integrations.common.base_client import RawExternalResponse


def fetch(response: RawExternalResponse) -> RawExternalResponse:
    """Pass the raw response envelope to storage without parsing it."""

    return response

