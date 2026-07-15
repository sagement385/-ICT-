"""Health and readiness endpoints."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.database import check_database_connection
from app.core.errors import ApplicationError

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Return process health without contacting optional dependencies."""

    return {"status": "ok", "service": "backend", "environment": get_settings().environment}


@router.get("/ready")
async def ready() -> dict[str, object]:
    """Return readiness only when the configured database responds."""

    database_ok, reason = await check_database_connection()
    if not database_ok:
        raise ApplicationError(
            code=reason or "DATABASE_CONNECTION_FAILED",
            message="필수 데이터베이스 연결이 준비되지 않았습니다.",
            details={"database": "not_ready"},
        )
    return {"status": "ready", "checks": {"database": "ok"}}

