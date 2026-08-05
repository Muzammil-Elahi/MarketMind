"""Tests for src/recommendation/similarity.py (D-02, content-based
profile-archetype <-> asset similarity sub-score).

Pure, zero-I/O numpy fixtures -- no network calls, no yfinance, no
Streamlit. Mirrors tests/test_recommendation_profile_fit.py's style.
"""

import inspect

import numpy as np

from src.recommendation.similarity import (
    RISK_ARCHETYPES,
    cosine_similarity,
    similarity_score,
)


def test_cosine_similarity_identical_vectors_returns_one():
    assert cosine_similarity(np.array([1.0, 0.0]), np.array([1.0, 0.0])) == 1.0


def test_cosine_similarity_zero_vector_guard_returns_zero():
    assert cosine_similarity(np.array([0.0, 0.0]), np.array([1.0, 0.0])) == 0.0


def test_risk_archetypes_has_exactly_three_expected_keys():
    assert set(RISK_ARCHETYPES.keys()) == {"Conservative", "Moderate", "Aggressive"}


def test_similarity_score_high_momentum_low_volatility_favors_aggressive():
    aggressive_score = similarity_score(
        momentum_score=0.9, volatility_score=0.2, risk_tolerance="Aggressive"
    )
    conservative_score = similarity_score(
        momentum_score=0.9, volatility_score=0.2, risk_tolerance="Conservative"
    )

    assert aggressive_score > conservative_score


def test_similarity_score_unknown_risk_tolerance_falls_back_to_moderate():
    fallback_score = similarity_score(
        momentum_score=0.6, volatility_score=0.6, risk_tolerance="NotARealTier"
    )
    moderate_score = similarity_score(
        momentum_score=0.6, volatility_score=0.6, risk_tolerance="Moderate"
    )

    assert fallback_score == moderate_score


def test_similarity_score_is_deterministic_across_repeated_calls():
    first_call = similarity_score(
        momentum_score=0.5, volatility_score=0.4, risk_tolerance="Moderate"
    )
    second_call = similarity_score(
        momentum_score=0.5, volatility_score=0.4, risk_tolerance="Moderate"
    )

    assert first_call == second_call


def test_similarity_score_bounded_zero_to_one_for_unit_interval_inputs():
    for momentum in (0.0, 0.25, 0.5, 0.75, 1.0):
        for volatility in (0.0, 0.25, 0.5, 0.75, 1.0):
            for risk_tolerance in RISK_ARCHETYPES:
                score = similarity_score(momentum, volatility, risk_tolerance)
                assert 0.0 <= score <= 1.0


def test_similarity_score_signature_has_no_interaction_history_channel():
    """Structural proof of the cold-start non-issue: the function's
    signature has no parameter through which prior interaction history
    could even be threaded."""
    params = set(inspect.signature(similarity_score).parameters.keys())

    assert params == {"momentum_score", "volatility_score", "risk_tolerance"}
    assert "user_id" not in params
    assert "session" not in params
    assert "history" not in params
