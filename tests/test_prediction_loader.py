"""Tests for src/pages/_prediction_loader.py (PRED-01/PRED-02, D-07/D-08).

Mirrors tests/test_universe_loader.py's unittest.mock.patch style: mock
src.pages._prediction_loader.fetch_ohlcv directly (the name as imported
into this module) rather than exercising the real yfinance chokepoint. No
live network call occurs anywhere in this file.
"""

from unittest.mock import patch

import numpy as np
import pandas as pd

from src.pages._prediction_loader import fetch_prediction_data
from src.prediction.walk_forward import MIN_PREDICTION_HISTORY_ROWS


def _sample_ohlcv(n_rows: int) -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", periods=n_rows, freq="D")
    close = pd.Series(
        100 + np.sin(np.arange(n_rows) / 3.0) * 5 + np.arange(n_rows) * 0.05,
        index=dates,
        dtype=float,
    )
    return pd.DataFrame(
        {"Open": close, "High": close + 1, "Low": close - 1, "Close": close}
    )


def _n_rows_for_target_feature_rows(target: int) -> int:
    """Compute the exact raw row count that yields exactly ``target``
    post-dropna feature rows, rather than guessing a warm-up constant.

    Once past the rolling-window warm-up region, every additional raw row
    adds exactly one post-dropna feature row (the indicators are causal,
    backward-looking transformations) -- so the warm-up row count is a
    fixed offset, independent of ``n_rows``, that we can measure once via
    a generously over-provisioned probe frame.
    """
    from src.features.feature_frame import assemble_feature_frame

    probe_n = target + 100
    probe_df = _sample_ohlcv(probe_n)
    probe_features = assemble_feature_frame(probe_df).dropna()
    warm_up = probe_n - len(probe_features)
    return target + warm_up


def _fixture_with_exact_feature_rows(target: int) -> pd.DataFrame:
    from src.features.feature_frame import assemble_feature_frame

    n_rows = _n_rows_for_target_feature_rows(target)
    df = _sample_ohlcv(n_rows)
    actual = len(assemble_feature_frame(df).dropna())
    assert actual == target, (
        f"fixture self-check failed: expected {target} post-dropna feature "
        f"rows, got {actual} (n_rows={n_rows})"
    )
    return df


def test_fetch_prediction_data_not_found_on_exception():
    with patch(
        "src.pages._prediction_loader.fetch_ohlcv",
        side_effect=RuntimeError("simulated failure"),
    ):
        result = fetch_prediction_data("NOTATICKER")

    assert result == {"status": "not_found"}


def test_fetch_prediction_data_not_found_on_empty_dataframe():
    with patch(
        "src.pages._prediction_loader.fetch_ohlcv",
        return_value=(pd.DataFrame(), "live"),
    ):
        result = fetch_prediction_data("NOTATICKER")

    assert result == {"status": "not_found"}


def test_fetch_prediction_data_calls_fetch_ohlcv_with_5y_period():
    full_df = _sample_ohlcv(n_rows=1300)
    with patch(
        "src.pages._prediction_loader.fetch_ohlcv",
        return_value=(full_df, "live"),
    ) as mock_fetch:
        fetch_prediction_data("AAPL")

    mock_fetch.assert_called_once_with("AAPL", period="5y")


def test_fetch_prediction_data_insufficient_data_at_749_rows():
    assert MIN_PREDICTION_HISTORY_ROWS == 750
    thin_df = _fixture_with_exact_feature_rows(749)

    with patch(
        "src.pages._prediction_loader.fetch_ohlcv",
        return_value=(thin_df, "live"),
    ):
        result = fetch_prediction_data("THINHIST")

    assert result["status"] == "insufficient_data"
    pd.testing.assert_frame_equal(result["chart_df"], thin_df)


def test_fetch_prediction_data_ok_at_750_rows_boundary():
    assert MIN_PREDICTION_HISTORY_ROWS == 750
    full_df = _fixture_with_exact_feature_rows(750)

    with patch(
        "src.pages._prediction_loader.fetch_ohlcv",
        return_value=(full_df, "live"),
    ):
        result = fetch_prediction_data("FULLHIST")

    assert result["status"] == "ok"
    pd.testing.assert_frame_equal(result["chart_df"], full_df)

    feature_frame = result["feature_frame"]
    price_series = result["price_series"]

    assert len(feature_frame) == 750
    assert not feature_frame.isna().any().any()
    assert price_series.index.equals(feature_frame.index)
    assert len(result["chart_df"]) > len(feature_frame)
    assert len(result["chart_df"]) > len(price_series)
