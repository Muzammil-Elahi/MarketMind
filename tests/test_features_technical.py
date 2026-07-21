"""Tests for src/features/technical.py and feature_frame.py (PROFILE-01).

All tests operate on a small deterministic synthetic OHLCV DataFrame --
no network calls, no yfinance, no Streamlit. src/features/ is a pure,
zero-I/O module: these tests exercise that contract directly.
"""

import numpy as np
import pandas as pd
import pytest

from src.features.feature_frame import assemble_feature_frame
from src.features.technical import (
    compute_returns,
    compute_rsi,
    compute_sma,
    compute_volatility,
)


def _sample_ohlcv(n_rows: int = 40) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n_rows, freq="D")
    # A simple upward-trending close series with a bit of variation so RSI
    # and volatility are non-degenerate.
    close = pd.Series(
        100 + np.sin(np.arange(n_rows) / 3.0) * 5 + np.arange(n_rows) * 0.5,
        index=dates,
        dtype=float,
    )
    return pd.DataFrame(
        {"Open": close, "High": close + 1, "Low": close - 1, "Close": close}
    )


def test_compute_returns_is_pct_change_aligned_to_index():
    df = _sample_ohlcv()

    result = compute_returns(df)

    pd.testing.assert_series_equal(
        result, df["Close"].pct_change(), check_names=False
    )
    assert result.index.equals(df.index)
    assert pd.isna(result.iloc[0])


def test_compute_volatility_matches_rolling_std_of_returns_never_centered():
    df = _sample_ohlcv()
    window = 20

    result = compute_volatility(df, window=window)
    expected = compute_returns(df).rolling(window, center=False).std()

    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_compute_sma_matches_plain_rolling_mean_never_centered():
    df = _sample_ohlcv()
    window = 20

    result = compute_sma(df, window=window)
    expected = df["Close"].rolling(window, center=False).mean()

    np.testing.assert_allclose(
        result.to_numpy(dtype=float), expected.to_numpy(dtype=float)
    )


def test_compute_rsi_is_series_same_length_bounded_zero_to_hundred():
    df = _sample_ohlcv()

    result = compute_rsi(df, window=14)

    assert len(result) == len(df)
    non_na = result.dropna()
    assert not non_na.empty
    assert (non_na >= 0).all()
    assert (non_na <= 100).all()


def test_assemble_feature_frame_has_exact_expected_columns_and_index():
    df = _sample_ohlcv()

    result = assemble_feature_frame(df)

    assert result.index.equals(df.index)
    assert list(result.columns) == ["returns", "volatility_20", "sma_20", "rsi_14"]


def test_assemble_feature_frame_truncation_invariance():
    """Features for rows <= T must be identical whether the raw frame ends
    at T or extends further into the future -- proves no later row changes
    an earlier feature value (D-11)."""
    full_df = _sample_ohlcv(70)
    truncated_df = full_df.iloc[:50]

    features_from_truncated = assemble_feature_frame(truncated_df)
    features_from_full = assemble_feature_frame(full_df).iloc[:50]

    pd.testing.assert_frame_equal(features_from_truncated, features_from_full)


@pytest.mark.parametrize("fn_name", ["technical", "feature_frame"])
def test_module_has_no_center_true_or_negative_shift(fn_name):
    """Structural guard mirroring the plan's automated verify grep -- belt
    and suspenders alongside the actual leakage smoke test."""
    import inspect

    from src.features import feature_frame, technical

    module = technical if fn_name == "technical" else feature_frame
    source = inspect.getsource(module)

    assert "center=True" not in source
    assert ".shift(-" not in source
    assert "import streamlit" not in source
