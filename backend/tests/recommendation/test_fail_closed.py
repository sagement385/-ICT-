"""Tests for recommendation stages that remain policy controlled."""

import pytest

from app.core.errors import ApplicationError
from app.modules.recommendation.feature_builder import FeatureBuilder
from app.modules.recommendation.score_calculator import ScoreCalculator


def test_feature_builder_does_not_invent_medical_features() -> None:
    """An empty source set produces no synthetic hospital features."""

    features = FeatureBuilder().build(  # type: ignore[arg-type]
        patient={},
        hospitals=[],
        route_data={},
        realtime_status={},
    )

    assert features == {}


def test_score_calculator_does_not_apply_default_weights() -> None:
    """Scoring stops instead of applying hard-coded medical weights."""

    with pytest.raises(ApplicationError) as error:
        ScoreCalculator().calculate(features={}, weights={})

    assert error.value.code == "RECOMMENDATION_POLICY_NOT_CONFIGURED"
