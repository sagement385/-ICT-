import pytest

from app.core.errors import ApplicationError
from app.integrations.nemc.client import _add_region_params


def test_nemc_region_params_use_documented_names() -> None:
    params: dict[str, str | int] = {}
    _add_region_params(params, "TEST_STAGE1", "TEST_STAGE2")
    assert params == {"STAGE1": "TEST_STAGE1", "STAGE2": "TEST_STAGE2"}


def test_nemc_region_params_reject_incomplete_filter() -> None:
    with pytest.raises(ApplicationError) as error_info:
        _add_region_params({}, "TEST_STAGE1", None)
    assert error_info.value.code == "NEMC_REGION_FILTER_INCOMPLETE"
