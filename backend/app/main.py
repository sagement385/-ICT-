"""FastAPI application composition without business logic in the entrypoint."""

from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from app.api.v1.router import router as api_router
from app.core.config import get_settings
from app.core.errors import ApplicationError, error_body
from app.core.logging import configure_logging

configure_logging(get_settings().log_level)
app = FastAPI(
    title="Chungbuk 119 Emergency Decision Support API",
    version="0.1.0",
    description="의료 의사결정을 대체하지 않는 응급환자 병원·경로 지원 API",
)
app.include_router(api_router)


@app.middleware("http")
async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach a correlation id without exposing request bodies in logs."""

    request.state.request_id = request.headers.get("X-Request-ID", str(uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.exception_handler(ApplicationError)
async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    """Serialize known failures into the stable error envelope."""

    request_id = str(getattr(request.state, "request_id", "unknown-request"))
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc, request_id),
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return validation failures with the same request correlation id."""

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "REQUEST_VALIDATION_ERROR",
                "message": "요청 형식이 유효하지 않습니다.",
                "details": {"errors": exc.errors()},
                "request_id": str(getattr(request.state, "request_id", "unknown-request")),
            }
        },
    )
