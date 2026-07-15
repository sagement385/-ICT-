"""FastAPI application composition without business logic in the entrypoint."""

import logging
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.router import router as api_router
from app.core.config import get_settings
from app.core.errors import ApplicationError, error_body
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)
app = FastAPI(
    title="Chungbuk 119 Emergency Decision Support API",
    version="0.1.0",
    description="의료 의사결정을 대체하지 않는 응급환자 병원·경로 지원 API",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Return a stable database failure without exposing SQL or credentials."""

    request_id = str(getattr(request.state, "request_id", "unknown-request"))
    logger.error(
        "database operation failed request_id=%s path=%s error_type=%s",
        request_id,
        request.url.path,
        type(exc).__name__,
    )
    return JSONResponse(
        status_code=503,
        content=error_body(
            ApplicationError(
                code="DATABASE_OPERATION_FAILED",
                message="데이터베이스 작업을 완료하지 못했습니다.",
                details={},
            ),
            request_id,
        ),
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Convert uncaught domain value errors into a safe validation envelope."""

    del exc
    request_id = str(getattr(request.state, "request_id", "unknown-request"))
    return JSONResponse(
        status_code=422,
        content=error_body(
            ApplicationError(
                code="REQUEST_VALUE_INVALID",
                message="요청 값이 허용된 범위를 벗어났습니다.",
                status_code=422,
                details={},
            ),
            request_id,
        ),
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Hide internal exception details while retaining a request-id log trail."""

    request_id = str(getattr(request.state, "request_id", "unknown-request"))
    logger.error(
        "unexpected API failure request_id=%s path=%s error_type=%s",
        request_id,
        request.url.path,
        type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content=error_body(
            ApplicationError(
                code="INTERNAL_SERVER_ERROR",
                message="요청 처리 중 내부 오류가 발생했습니다.",
                status_code=500,
                details={},
            ),
            request_id,
        ),
    )
