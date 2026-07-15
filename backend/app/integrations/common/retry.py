"""Small retry policy helpers for transient HTTP failures."""


def exponential_backoff(attempt: int, base_seconds: float = 0.25, maximum_seconds: float = 8.0) -> float:
    """Return a bounded delay for a zero-based retry attempt."""

    return min(maximum_seconds, base_seconds * (2**attempt))

