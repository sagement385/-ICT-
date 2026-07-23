"""FastAPI dependency helpers shared by routers."""

import httpx
from fastapi import Request


def get_request_id(request: Request) -> str:
    """Read the request id assigned by the application middleware."""

    return str(getattr(request.state, "request_id", "unknown-request"))


def get_external_http_client(request: Request) -> httpx.AsyncClient:
    """Return the lifespan-managed HTTP client used by runtime integrations."""

    client = getattr(request.app.state, "external_http_client", None)
    if not isinstance(client, httpx.AsyncClient):
        raise RuntimeError("application external HTTP client is not initialized")
    return client
