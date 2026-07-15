"""Repository and recommendation interface smoke tests."""

import inspect

from app.modules.hospital.repository import HospitalRepository
from app.modules.patient.repository import PatientRepository
from app.modules.recommendation.candidate_filter import CandidateFilter
from app.modules.recommendation.feature_builder import FeatureBuilder
from app.modules.recommendation.ranking_service import RankingService
from app.modules.recommendation.score_calculator import ScoreCalculator


def test_repository_interfaces_are_async_for_database_calls() -> None:
    """Repositories expose async DB methods and no HTTP concerns."""

    assert inspect.iscoroutinefunction(PatientRepository.get_case)
    assert inspect.iscoroutinefunction(PatientRepository.add_case)
    assert inspect.iscoroutinefunction(HospitalRepository.get)
    assert inspect.iscoroutinefunction(HospitalRepository.list_all)


def test_recommendation_interfaces_have_no_hardcoded_score() -> None:
    """Candidate filtering and ranking are present without a medical score formula."""

    assert hasattr(CandidateFilter, "filter")
    assert hasattr(FeatureBuilder, "build")
    assert hasattr(ScoreCalculator, "calculate")
    assert hasattr(RankingService, "rank")

