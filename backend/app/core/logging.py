"""Minimal structured logging setup used by API and integration boundaries."""

import logging


def configure_logging(level: str) -> None:
    """Configure a predictable console logger without logging secrets or payloads."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

