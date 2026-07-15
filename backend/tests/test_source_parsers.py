import json
from pathlib import Path

import pytest

from app.core.errors import ApplicationError
from app.integrations.hira.detail_parser import parse_detail
from app.integrations.hira.parser import parse_basic_hospitals
from app.integrations.hira.parser import parse_total_count as parse_hira_total_count
from app.integrations.nemc.parser import parse_realtime_records
from app.integrations.nemc.parser import parse_total_count as parse_nemc_total_count

FIXTURES = Path(__file__).parent / "fixtures"


def test_hira_basic_fixture_is_normalized() -> None:
    payload = (FIXTURES / "hira-basic-test.xml").read_text(encoding="utf-8")
    hospitals = parse_basic_hospitals(payload)
    assert parse_hira_total_count(payload) == 1
    assert hospitals[0].hospital_id == "TEST_HOSPITAL_001_ID"
    assert hospitals[0].latitude == 36.0001


def test_nemc_fixture_preserves_raw_status_fields() -> None:
    payload = (FIXTURES / "nemc-realtime-test.xml").read_text(encoding="utf-8")
    records = parse_realtime_records(payload)
    assert parse_nemc_total_count(payload) == 1
    assert records[0].source_record_id == "TEST_NEMC_001"
    assert records[0].raw_fields["hvs01"] == "TEST_RAW_STATUS"


def test_hira_detail_fixture_normalizes_verified_department_fields() -> None:
    payload = json.loads((FIXTURES / "hira-detail-test.json").read_text(encoding="utf-8"))
    result = parse_detail("getDgsbjtInfo2.8", payload)
    assert result.departments[0].department_code == "TEST_DEPARTMENT_CODE_001"
    assert result.departments[0].specialist_count == 2


def test_hira_equipment_fixture_uses_only_live_sample_confirmed_fields() -> None:
    payload = json.loads((FIXTURES / "hira-equipment-test.json").read_text(encoding="utf-8"))
    result = parse_detail("getMedOftInfo2.8", payload)
    assert result.equipment[0].equipment_code == "TEST_EQUIPMENT_CODE_001"
    assert result.equipment[0].equipment_count == 2


@pytest.mark.parametrize(
    ("parser", "expected_code"),
    [
        (parse_basic_hospitals, "HIRA_PROVIDER_ERROR"),
        (parse_realtime_records, "NEMC_PROVIDER_ERROR"),
    ],
)
def test_http_200_provider_error_envelopes_are_not_treated_as_empty_success(
    parser: object,
    expected_code: str,
) -> None:
    """A confirmed non-success resultCode is surfaced even with an HTTP 200 body."""

    payload = (FIXTURES / "provider-error-test.xml").read_text(encoding="utf-8")
    with pytest.raises(ApplicationError) as error:
        parser(payload)  # type: ignore[operator]
    assert error.value.code == expected_code
