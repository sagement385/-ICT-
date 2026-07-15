"""Tests for recommendation stages that must remain fail-closed."""

import pytest

from app.core.errors import ApplicationError
from app.modules.recommendation.feature_builder import FeatureBuilder
from app.modules.recommendation.score_calculator import ScoreCalculator


def test_feature_builder_does_not_invent_medical_features() -> None:
    """Feature generation stops until approved feature definitions exist."""

    with pytest.raises(ApplicationError) as error:
        FeatureBuilder().build(  # type: ignore[arg-type]
            patient={},
            hospitals=[],
            route_data={},
            realtime_status={},
        )

    assert error.value.code == "RECOMMENDATION_FEATURES_NOT_IMPLEMENTED"


def test_score_calculator_does_not_apply_default_weights() -> None:
    """Scoring stops instead of applying hard-coded medical weights."""

    with pytest.raises(ApplicationError) as error:
        ScoreCalculator().calculate(features={}, weights={})

    assert error.value.code == "RECOMMENDATION_SCORING_NOT_IMPLEMENTED"

