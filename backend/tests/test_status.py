"""Operational status endpoint tests with an isolated empty database."""

from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.database import Base, get_db_session
from app.main import app


@pytest.mark.asyncio
async def test_status_explains_empty_data_without_credentials() -> None:
    """The dashboard receives explicit zero coverage and no secret configuration values."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/status")
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "limited"
    assert payload["data"]["hospitals"] == 0
    assert payload["data"]["source_identities_verified"] == 0
    assert payload["data"]["source_identities_unverified"] == 0
    assert payload["readiness"]["policy_recommendation"] is False
    assert "RECOMMENDATION_POLICY_NOT_CONFIGURED" in payload["warnings"]
    serialized = response.text.lower()
    assert "api_key" not in serialized
    assert "client_secret" not in serialized
