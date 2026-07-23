"""Run NEMC realtime synchronization at an explicitly configured interval."""

import argparse
import asyncio
import logging
from time import monotonic

from app.core.config import get_settings
from app.core.logging import configure_logging
from scripts.sync_realtime_status import sync_realtime_status

logger = logging.getLogger(__name__)


async def run_worker(*, once: bool = False) -> None:
    """Run one collection or repeat only when an interval was configured."""

    settings = get_settings()
    interval = settings.nemc_sync_interval_seconds
    if not once and interval is None:
        raise RuntimeError(
            "NEMC_SYNC_INTERVAL_SECONDS must be configured for the recurring worker"
        )

    while True:
        started = monotonic()
        try:
            loaded = await sync_realtime_status()
            logger.info("NEMC realtime cycle completed loaded=%s", loaded)
        except Exception as error:
            logger.error(
                "NEMC realtime cycle failed error_type=%s",
                type(error).__name__,
            )
            if once:
                raise
        if once:
            return
        assert interval is not None
        await asyncio.sleep(max(1.0, interval - (monotonic() - started)))


def parse_args() -> argparse.Namespace:
    """Parse the explicit one-shot override used for diagnostics."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--once",
        action="store_true",
        help="run one synchronization without requiring an interval",
    )
    return parser.parse_args()


def main() -> None:
    """Configure safe logging and start the worker."""

    args = parse_args()
    configure_logging(get_settings().log_level)
    asyncio.run(run_worker(once=bool(args.once)))


if __name__ == "__main__":
    main()
