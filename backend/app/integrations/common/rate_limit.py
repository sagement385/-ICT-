"""Rate-limit response classification shared by external clients."""


def is_rate_limited(status_code: int) -> bool:
    """Return whether a provider asks the caller to slow down."""

    return status_code in {408, 425, 429, 503}

