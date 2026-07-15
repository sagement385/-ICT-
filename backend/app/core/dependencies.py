"""FastAPI dependency helpers shared by routers."""

from fastapi import Request


def get_request_id(request: Request) -> str:
    """Read the request id assigned by the application middleware."""

    return str(getattr(request.state, "request_id", "unknown-request"))

