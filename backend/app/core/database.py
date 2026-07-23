"""Lazy SQLAlchemy 2 async database access."""

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings
from app.core.errors import ApplicationError


class Base(DeclarativeBase):
    """Base class for all database models."""


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Create the async engine only when a configured database is needed."""

    global _engine
    if _engine is None:
        database_url = get_settings().database_url
        if not database_url:
            raise ApplicationError(
                code="DATABASE_NOT_CONFIGURED",
                message="DATABASE_URL이 설정되지 않았습니다.",
                details={"missing_settings": ["DATABASE_URL"]},
            )
        _engine = create_async_engine(database_url, pool_pre_ping=True)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the lazy async session factory."""

    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield a database session or a configuration error."""

    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


async def check_database_connection() -> tuple[bool, str | None]:
    """Check database connectivity for the readiness endpoint."""

    try:
        engine = get_engine()
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except ApplicationError as error:
        return False, error.code
    except SQLAlchemyError:
        return False, "DATABASE_CONNECTION_FAILED"
    return True, None


async def close_database() -> None:
    """Dispose the process-wide engine during application shutdown."""

    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
