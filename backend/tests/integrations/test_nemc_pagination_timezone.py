"""NEMC pagination and source-timezone tests using a redacted XML fixture."""

from datetime import timedelta
from pathlib import Path

import pytest

from app.core.errors import ApplicationError
from app.integrations.nemc.parser import (
    calculate_total_pages,
    parse_realtime_records,
    parse_total_count,
)

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "nemc-realtime-test.xml"


@pytest.mark.parametrize(
    ("total_count", "expected_pages"),
    [
        (0, 1),
        (1, 1),
        (999, 1),
        (1000, 1),
        (1001, 2),
        (1500, 2),
        (2000, 2),
    ],
)
def test_nemc_total_pages_handles_boundaries(
    total_count: int,
    expected_pages: int,
) -> None:
    """A 1000-row request neither skips nor repeats a boundary page."""

    assert calculate_total_pages(total_count, 1000) == expected_pages


def test_nemc_timestamp_stays_unknown_without_verified_timezone() -> None:
    """A timezone-free provider value is preserved raw instead of using host timezone."""

    payload = FIXTURE_PATH.read_text(encoding="utf-8")
    record = parse_realtime_records(payload)[0]

    assert record.source_updated_at is None
    assert record.source_updated_at_raw == "20260715120000"
    assert record.source_timezone == "unknown"


def test_nemc_timestamp_uses_explicit_iana_timezone() -> None:
    """An explicitly verified timezone produces an aware datetime via ZoneInfo."""

    payload = FIXTURE_PATH.read_text(encoding="utf-8")
    record = parse_realtime_records(payload, source_timezone="Asia/Seoul")[0]

    assert record.source_updated_at is not None
    assert record.source_updated_at.utcoffset() == timedelta(hours=9)
    assert record.source_timezone == "Asia/Seoul"


def test_nemc_invalid_timezone_is_a_safe_configuration_error() -> None:
    """An invalid timezone setting is never replaced with the host timezone."""

    payload = FIXTURE_PATH.read_text(encoding="utf-8")
    with pytest.raises(ApplicationError) as error:
        parse_realtime_records(payload, source_timezone="TEST_INVALID_TIMEZONE")
    assert error.value.code == "NEMC_SOURCE_TIMEZONE_INVALID"


def test_nemc_invalid_total_count_does_not_silently_skip_pages() -> None:
    """Malformed pagination metadata stops collection instead of becoming zero rows."""

    payload = (
        FIXTURE_PATH.parent / "nemc-invalid-total-count-test.xml"
    ).read_text(encoding="utf-8")
    with pytest.raises(ApplicationError) as error:
        parse_total_count(payload)
    assert error.value.code == "NEMC_PAGINATION_INVALID"
