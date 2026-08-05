"""Tests for src/recommendation/engine.py (REC-01/REC-02/REC-03, D-05).

Pure, zero-I/O synthetic-DataFrame fixtures -- no network calls, no
yfinance, no Streamlit. Mirrors tests/test_features_technical.py's
synthetic-data style and the other tests/test_recommendation_*.py files.
"""

import pandas as pd

from src.recommendation import engine, explain
from src.recommendation.engine import (
    TOP_N_PER_CLASS,
    WEIGHTS,
    _compose_score,
    _round_half_up,
    build_recommendations,
    score_universe,
)
from src.recommendation.explain import SUB_SCORE_ORDER
from src.recommendation.universe import ASSET_CLASSES

UNIVERSE_COLUMNS = ["ticker", "asset_class", "sector", "returns", "volatility_20", "rsi_14"]


def _synthetic_universe_df():
    """3 Stocks + 3 Crypto rows, internally varied on every raw factor."""
    return pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC", "XXX", "YYY", "ZZZ"],
            "asset_class": ["Stocks"] * 3 + ["Crypto"] * 3,
            "sector": ["Tech", "Healthcare", "Energy", None, None, None],
            "returns": [0.05, 0.02, -0.01, 0.10, 0.03, -0.02],
            "volatility_20": [0.15, 0.20, 0.25, 0.40, 0.35, 0.30],
            "rsi_14": [55, 50, 45, 60, 50, 40],
        }
    )


def _minimal_profile(**overrides):
    profile = {
        "risk_tolerance": "Moderate",
        "excluded_sectors": [],
        "preferred_asset_types": [],
        "preferred_sectors": [],
        "time_horizon": None,
    }
    profile.update(overrides)
    return profile


# --- Task 1: score_universe ---------------------------------------------


def test_weights_sum_to_one():
    assert sum(WEIGHTS.values()) == 1.0


def test_score_universe_empty_universe_returns_empty_without_raising():
    profile = _minimal_profile()
    empty_df = pd.DataFrame(columns=UNIVERSE_COLUMNS)

    result = score_universe(profile, empty_df)

    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_score_universe_composite_score_bounded_zero_to_hundred():
    df = _synthetic_universe_df()
    profile = _minimal_profile()

    result = score_universe(profile, df)

    assert not result.empty
    assert (result["composite_score"] >= 0.0).all()
    assert (result["composite_score"] <= 100.0).all()


def test_compose_score_and_round_half_up_82_5_rounds_to_83_not_82():
    """REC-02 precision: round-half-up, never Python's banker's-rounding."""
    sub_scores = {key: 0.825 for key in WEIGHTS}

    composite = _compose_score(sub_scores)

    assert composite == 82.5
    assert _round_half_up(composite) == 83
    assert round(composite) == 82  # documents why round() is not used


def test_compose_score_clamps_theoretical_min_and_max_to_zero_and_hundred():
    min_sub_scores = {key: 0.0 for key in WEIGHTS}
    max_sub_scores = {key: 1.0 for key in WEIGHTS}

    assert _compose_score(min_sub_scores) == 0.0
    assert _compose_score(max_sub_scores) == 100.0


def test_score_universe_excludes_sector_by_default_but_includes_when_bypassed():
    df = _synthetic_universe_df()
    profile = _minimal_profile(excluded_sectors=["Tech"])

    hard_excluded_result = score_universe(profile, df, apply_hard_exclude=True)
    assert "AAA" not in hard_excluded_result["ticker"].values

    bypassed_result = score_universe(profile, df, apply_hard_exclude=False)
    assert "AAA" in bypassed_result["ticker"].values

    # REC-04 single-source-of-truth: the bypassed row uses the identical
    # scoring formula as a row that was never excluded in the first place --
    # both compute against the same unfiltered 6-row eligible universe.
    fully_included_result = score_universe(_minimal_profile(), df, apply_hard_exclude=True)
    bypass_score = bypassed_result.loc[bypassed_result["ticker"] == "AAA", "composite_score"].iloc[0]
    full_score = fully_included_result.loc[fully_included_result["ticker"] == "AAA", "composite_score"].iloc[0]
    assert bypass_score == full_score


def test_score_universe_excluded_asset_absent_even_with_favorable_raw_scores():
    """T-03-04: the hard-exclude filter runs before any factor/composite
    computation -- an excluded asset never appears regardless of how
    favorable its raw factor values are."""
    df = pd.DataFrame(
        {
            "ticker": ["EXCLUDED_BEST", "OTHER1", "OTHER2"],
            "asset_class": ["Stocks"] * 3,
            "sector": ["Energy", "Tech", "Tech"],
            "returns": [0.50, 0.01, 0.02],
            "volatility_20": [0.01, 0.20, 0.25],
            "rsi_14": [50, 50, 50],
        }
    )
    profile = _minimal_profile(excluded_sectors=["Energy"])

    result = score_universe(profile, df)

    assert "EXCLUDED_BEST" not in result["ticker"].values


def test_score_universe_ties_broken_by_ticker_ascending():
    df = pd.DataFrame(
        {
            "ticker": ["BBB", "AAA"],
            "asset_class": ["Gold", "Gold"],
            "sector": [None, None],
            "returns": [0.02, 0.02],
            "volatility_20": [0.05, 0.05],
            "rsi_14": [50, 50],
        }
    )
    profile = _minimal_profile()

    result = score_universe(profile, df)

    assert result["composite_score"].iloc[0] == result["composite_score"].iloc[1]
    assert list(result["ticker"]) == ["AAA", "BBB"]


def test_score_universe_sub_scores_key_order_matches_sub_score_order():
    df = _synthetic_universe_df()
    profile = _minimal_profile()

    result = score_universe(profile, df)

    for sub_scores in result["sub_scores"]:
        assert list(sub_scores.keys()) == SUB_SCORE_ORDER


def test_score_universe_explanation_uses_rows_own_sub_scores():
    df = _synthetic_universe_df()
    profile = _minimal_profile()

    result = score_universe(profile, df)

    for _, row in result.iterrows():
        expected = explain.explain(row["sub_scores"], profile.get("risk_tolerance"))
        assert row["explanation"] == expected


def test_score_universe_composite_score_display_is_round_half_up_of_composite_score():
    df = _synthetic_universe_df()
    profile = _minimal_profile()

    result = score_universe(profile, df)

    for _, row in result.iterrows():
        assert row["composite_score_display"] == _round_half_up(row["composite_score"])
        for key, value in row["sub_scores"].items():
            assert row["sub_scores_display"][key] == _round_half_up(value * 100)


def test_score_universe_sorts_by_raw_composite_score_when_display_rounds_tie(monkeypatch):
    """REC-02 precision/ordering: ranking always uses the unrounded
    composite_score, so two rows whose rounded displays are equal still
    sort in raw-score order, not display-tied arbitrary order."""
    df = pd.DataFrame(
        {
            "ticker": ["LOW", "HIGH"],
            "asset_class": ["Gold", "Crypto"],
            "sector": [None, None],
            "returns": [0.0, 0.0],
            "volatility_20": [0.0, 0.0],
            "rsi_14": [50, 50],
        }
    )
    profile = _minimal_profile()
    fraction_by_ticker = {"LOW": 0.806, "HIGH": 0.813}

    def fake_factor(universe_df):
        return universe_df["ticker"].map(fraction_by_ticker)

    monkeypatch.setattr(engine.factor_scoring, "compute_momentum_score", fake_factor)
    monkeypatch.setattr(engine.factor_scoring, "compute_volatility_score", fake_factor)
    monkeypatch.setattr(engine.factor_scoring, "compute_quality_score", fake_factor)
    monkeypatch.setattr(
        engine.profile_fit,
        "compute_profile_fit",
        lambda asset_row, profile: fraction_by_ticker[asset_row["ticker"]],
    )
    monkeypatch.setattr(
        engine.similarity,
        "similarity_score",
        lambda momentum_score, volatility_score, risk_tolerance: momentum_score,
    )

    result = score_universe(profile, df)

    low_score = result.loc[result["ticker"] == "LOW", "composite_score"].iloc[0]
    high_score = result.loc[result["ticker"] == "HIGH", "composite_score"].iloc[0]
    assert round(low_score, 1) == 80.6
    assert round(high_score, 1) == 81.3
    # Both land in the same round-half-up display bucket...
    assert _round_half_up(low_score) == _round_half_up(high_score)
    # ...yet the output is still ordered by the unrounded raw score.
    assert list(result["ticker"]) == ["HIGH", "LOW"]


def test_score_universe_zero_network_imports():
    import inspect

    source = inspect.getsource(engine)
    forbidden = ["import streamlit", "import yfinance", "langgraph", "google.genai", "google_genai"]
    lowered = source.lower()
    for token in forbidden:
        assert token not in lowered


# --- Task 2: build_recommendations --------------------------------------


def test_build_recommendations_returns_all_asset_classes_as_keys():
    df = _synthetic_universe_df()
    profile = _minimal_profile()

    result = build_recommendations(profile, df)

    assert list(result.keys()) == ASSET_CLASSES
    assert result["ETFs"] == []
    assert result["Gold"] == []
    assert result["Forex"] == []


def test_build_recommendations_empty_input_returns_all_classes_as_empty_lists():
    profile = _minimal_profile()
    empty_df = pd.DataFrame(columns=UNIVERSE_COLUMNS)

    result = build_recommendations(profile, empty_df)

    assert list(result.keys()) == ASSET_CLASSES
    assert all(value == [] for value in result.values())


def test_build_recommendations_top_n_truncates_and_orders_by_score_desc():
    df = pd.DataFrame(
        {
            "ticker": ["A", "B", "C", "D", "E"],
            "asset_class": ["Stocks"] * 5,
            "sector": [None] * 5,
            "returns": [0.10, 0.08, 0.06, 0.04, 0.02],
            "volatility_20": [0.10, 0.12, 0.14, 0.16, 0.18],
            "rsi_14": [55, 53, 51, 49, 47],
        }
    )
    profile = _minimal_profile()

    result = build_recommendations(profile, df, top_n=3)

    assert len(result["Stocks"]) == 3
    scores = [row["composite_score"] for row in result["Stocks"]]
    assert scores == sorted(scores, reverse=True)


def test_build_recommendations_partial_class_never_padded():
    df = pd.DataFrame(
        {
            "ticker": ["A", "B"],
            "asset_class": ["Gold", "Gold"],
            "sector": [None, None],
            "returns": [0.01, 0.02],
            "volatility_20": [0.05, 0.04],
            "rsi_14": [50, 52],
        }
    )
    profile = _minimal_profile()

    result = build_recommendations(profile, df, top_n=TOP_N_PER_CLASS)

    assert len(result["Gold"]) == 2


def test_build_recommendations_deterministic_across_calls():
    df = _synthetic_universe_df()
    profile = _minimal_profile()

    result1 = build_recommendations(profile, df)
    result2 = build_recommendations(profile, df)

    assert result1 == result2


def test_build_recommendations_rows_are_exact_score_universe_entries():
    df = _synthetic_universe_df()
    profile = _minimal_profile()
    expected_keys = {
        "ticker",
        "asset_class",
        "sector",
        "composite_score",
        "composite_score_display",
        "sub_scores",
        "sub_scores_display",
        "explanation",
    }

    result = build_recommendations(profile, df)

    for rows in result.values():
        for row in rows:
            assert set(row.keys()) == expected_keys
