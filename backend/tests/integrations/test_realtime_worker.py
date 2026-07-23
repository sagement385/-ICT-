"""NEMC worker scheduling tests without external API calls."""

from types import SimpleNamespace

import pytest

from scripts import run_realtime_sync_worker as worker


@pytest.mark.asyncio
async def test_recurring_worker_requires_explicit_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No arbitrary collection interval is selected by application code."""

    monkeypatch.setattr(
        worker,
        "get_settings",
        lambda: SimpleNamespace(nemc_sync_interval_seconds=None),
    )

    with pytest.raises(RuntimeError, match="NEMC_SYNC_INTERVAL_SECONDS"):
        await worker.run_worker()


@pytest.mark.asyncio
async def test_one_shot_worker_runs_without_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit diagnostic run performs exactly one mocked collection."""

    calls = 0

    async def fake_sync() -> int:
        nonlocal calls
        calls += 1
        return 1

    monkeypatch.setattr(
        worker,
        "get_settings",
        lambda: SimpleNamespace(nemc_sync_interval_seconds=None),
    )
    monkeypatch.setattr(worker, "sync_realtime_status", fake_sync)

    await worker.run_worker(once=True)

    assert calls == 1
