"""Tests for src/prediction/metrics.py (PRED-04, D-06's apples-to-apples
"Compare all models" requirement).

Pure, zero-I/O numpy fixtures -- no network calls, no yfinance, no
Streamlit. Mirrors tests/test_recommendation_similarity.py's style (small
deterministic arrays, no mocking).
"""

import numpy as np

from src.prediction.metrics import (
    DEFAULT_TRADING_DAYS_PER_YEAR,
    TRADING_DAYS_PER_YEAR,
    directional_accuracy,
    format_metrics_for_display,
    rmse,
    sharpe_ratio,
)


def test_rmse_identical_arrays_returns_zero():
    assert rmse(np.array([1.0, 2.0]), np.array([1.0, 2.0])) == 0.0


def test_rmse_single_unit_difference_returns_one():
    assert rmse(np.array([1.0]), np.array([2.0])) == 1.0


def test_directional_accuracy_all_matching_returns_one():
    predicted = np.array([1, -1, 1, 1, -1])
    actual = np.array([1, -1, 1, 1, -1])
    assert directional_accuracy(predicted, actual) == 1.0


def test_directional_accuracy_all_mismatching_returns_zero():
    predicted = np.array([1, 1, 1, 1, 1])
    actual = np.array([-1, -1, -1, -1, -1])
    assert directional_accuracy(predicted, actual) == 0.0


def test_directional_accuracy_partial_match_returns_fraction():
    predicted = np.array([1, 1, 1, -1, -1])
    actual = np.array([1, 1, 1, 1, 1])
    assert directional_accuracy(predicted, actual) == 0.6


def test_sharpe_ratio_zero_std_returns_zero_never_nan_or_inf():
    captured_returns = np.array([0.01, 0.01, 0.01, 0.01, 0.01])
    result = sharpe_ratio(captured_returns, "stocks")
    assert result == 0.0
    assert not np.isnan(result)
    assert not np.isinf(result)


def test_sharpe_ratio_crypto_differs_from_stocks_for_nonzero_variance():
    captured_returns = np.array([0.01, -0.02, 0.03, -0.01, 0.02])
    crypto_sharpe = sharpe_ratio(captured_returns, "crypto")
    stocks_sharpe = sharpe_ratio(captured_returns, "stocks")
    assert crypto_sharpe != stocks_sharpe


def test_sharpe_ratio_unrecognized_asset_class_falls_back_to_default():
    captured_returns = np.array([0.01, -0.02, 0.03, -0.01, 0.02])
    result = sharpe_ratio(captured_returns, "an-unrecognized-asset-class")
    periods_per_year = TRADING_DAYS_PER_YEAR.get(
        "an-unrecognized-asset-class", DEFAULT_TRADING_DAYS_PER_YEAR
    )
    assert periods_per_year == DEFAULT_TRADING_DAYS_PER_YEAR
    expected = float(
        captured_returns.mean()
        / captured_returns.std()
        * np.sqrt(DEFAULT_TRADING_DAYS_PER_YEAR)
    )
    assert result == expected


def test_format_metrics_for_display_uses_round_half_up_and_includes_all_keys():
    display = format_metrics_for_display(
        {"rmse": 12.345, "directional_accuracy": 0.625, "sharpe": 0.849}
    )
    assert set(display.keys()) == {"rmse", "directional_accuracy", "sharpe"}
    # Round-half-up (never Python's built-in round(), which is
    # banker's-rounding) -- 12.345 -> 12.35 (not 12.34), 0.849 -> 0.85.
    assert display["rmse"] == "12.35"
    assert display["directional_accuracy"] == "62.5%"
    assert display["sharpe"] == "0.85"


def test_format_metrics_for_display_round_half_up_regression_vs_python_round():
    # 0.6125 * 100 = 61.25 -- an exact half-way case at 1-decimal precision.
    # Python's built-in round() is banker's-rounding and rounds 61.25 down
    # to 61.2 (nearest even); round-half-up must round it up to 61.3,
    # matching REC-02's existing _round_half_up precedent.
    assert round(61.25, 1) == 61.2  # proves banker's-rounding would differ
    display = format_metrics_for_display(
        {"rmse": 0.0, "directional_accuracy": 0.6125, "sharpe": 0.0}
    )
    assert display["directional_accuracy"] == "61.3%"
