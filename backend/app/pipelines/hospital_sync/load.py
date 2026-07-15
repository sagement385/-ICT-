"""Hospital normalized loading stage."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError


async def load(session: AsyncSession, record: dict[str, Any]) -> None:
    """Remain disabled until the source-backed normalized schema exists."""

    del session, record
    raise ApplicationError(
        code="HOSPITAL_LOAD_NOT_IMPLEMENTED",
        message="검증된 병원 정규화 레코드 적재가 아직 없습니다.",
        details={},
    )

