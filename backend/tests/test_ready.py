"""Database failure readiness tests."""

import pytest

from app.core import database


@pytest.mark.asyncio
async def test_database_check_reports_missing_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Readiness reports configuration failure instead of claiming ready."""

    monkeypatch.setattr(database, "_engine", None)
    monkeypatch.setattr(database.get_settings(), "database_url", None)
    ok, reason = await database.check_database_connection()
    assert not ok
    assert reason == "DATABASE_NOT_CONFIGURED"

