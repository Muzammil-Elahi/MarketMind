"""Tests for src/recommendation/factor_scoring.py (REC-01/REC-02, D-03).

No network calls, no yfinance, no Streamlit -- factor_scoring.py is a pure,
zero-I/O module: these tests exercise that contract directly against
small, deterministic synthetic ``universe_df`` fixtures.
"""

import pandas as pd

from src.recommendation.factor_scoring import (
    DEFAULT_PERCENTILE_FALLBACK,
    MIN_GROUP_SIZE,
    compute_momentum_score,
    compute_quality_score,
    compute_volatility_score,
)


def _synthetic_universe_df():
    """5 Crypto + 4 Gold rows -- both groups >= MIN_GROUP_SIZE (3)."""
    return pd.DataFrame(
        {
            "asset_class": ["Crypto"] * 5 + ["Gold"] * 4,
            "returns": [0.10, 0.05, 0.02, -0.01, -0.05, 0.01, 0.02, 0.03, 0.015],
            "volatility_20": [0.40, 0.35, 0.30, 0.25, 0.20, 0.05, 0.04, 0.045, 0.038],
            "rsi_14": [70, 55, 50, 40, 30, 51, 49, 60, 45],
        }
    )


def test_compute_momentum_score_returns_series_aligned_in_unit_range():
    df = _synthetic_universe_df()

    result = compute_momentum_score(df)

    assert isinstance(result, pd.Series)
    assert result.index.equals(df.index)
    assert (result >= 0).all()
    assert (result <= 1).all()


def test_compute_volatility_score_returns_series_aligned_in_unit_range():
    df = _synthetic_universe_df()

    result = compute_volatility_score(df)

    assert isinstance(result, pd.Series)
    assert result.index.equals(df.index)
    assert (result >= 0).all()
    assert (result <= 1).all()


def test_compute_quality_score_returns_series_aligned_in_unit_range():
    df = _synthetic_universe_df()

    result = compute_quality_score(df)

    assert isinstance(result, pd.Series)
    assert result.index.equals(df.index)
    assert (result >= 0).all()
    assert (result <= 1).all()


def test_within_class_isolation_crypto_change_never_affects_gold_volatility_score():
    """Pitfall 1 regression: changing the Crypto row's raw volatility_20 must
    not change any Gold row's computed compute_volatility_score output."""
    df = _synthetic_universe_df()
    gold_mask = df["asset_class"] == "Gold"

    before = compute_volatility_score(df)

    df_mutated = df.copy()
    df_mutated.loc[df_mutated["asset_class"] == "Crypto", "volatility_20"] = 999.0
    after = compute_volatility_score(df_mutated)

    pd.testing.assert_series_equal(before[gold_mask], after[gold_mask])


def test_degenerate_group_falls_back_to_default_percentile_never_nan_or_inf():
    """Pitfall 2 regression: a group with fewer than MIN_GROUP_SIZE rows
    produces DEFAULT_PERCENTILE_FALLBACK for every row in that group on
    every factor score, never NaN/inf."""
    df = pd.DataFrame(
        {
            "asset_class": ["Gold", "Gold", "Crypto", "Crypto", "Crypto"],
            "returns": [0.01, 0.02, 0.10, 0.05, -0.02],
            "volatility_20": [0.05, 0.04, 0.40, 0.35, 0.20],
            "rsi_14": [50, 55, 70, 40, 30],
        }
    )
    assert (df["asset_class"] == "Gold").sum() < MIN_GROUP_SIZE
    gold_mask = df["asset_class"] == "Gold"

    for compute_fn in (compute_momentum_score, compute_volatility_score, compute_quality_score):
        result = compute_fn(df)
        assert not result.isna().any()
        assert not result.isin([float("inf"), float("-inf")]).any()
        assert (result[gold_mask] == DEFAULT_PERCENTILE_FALLBACK).all()


def test_compute_volatility_score_is_inverse_of_raw_volatility_percentile():
    """Lower raw volatility_20 within a class -> strictly highest
    compute_volatility_score in that class."""
    df = pd.DataFrame(
        {
            "asset_class": ["Stocks"] * 4 + ["Gold"] * 3,
            "returns": [0.01, 0.02, 0.03, 0.015, 0.01, 0.02, 0.015],
            "volatility_20": [0.02, 0.10, 0.15, 0.20, 0.05, 0.04, 0.045],
            "rsi_14": [50, 55, 45, 60, 50, 48, 52],
        }
    )
    result = compute_volatility_score(df)
    stocks_mask = df["asset_class"] == "Stocks"

    lowest_volatility_index = df.loc[stocks_mask, "volatility_20"].idxmin()
    assert result[lowest_volatility_index] == result[stocks_mask].max()
    assert (result[stocks_mask].drop(lowest_volatility_index) < result[lowest_volatility_index]).all()
