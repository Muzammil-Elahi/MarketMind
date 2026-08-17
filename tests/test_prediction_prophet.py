"""Tests for src/prediction/prophet_model.py (PRED-02/PRED-03).

Prophet fits are the slowest tests in this phase's suite (04-RESEARCH.md
Wave 0 Gaps), so exactly one real, non-mocked `forecast_forward` call is
made here -- the guard-path (RuntimeError when Prophet is unavailable) is
proven via `monkeypatch` instead of actually breaking the real installed
package.
"""

import numpy as np
import pandas as pd

from src.prediction import prophet_model


def _synthetic_close(n_rows: int = 75) -> pd.Series:
    """A small synthetic close-price Series with a mild upward trend + noise.

    Small enough (well under a full year of history) to keep Prophet's real
    fit fast, but well-defined enough (trend + noise, no NaNs/flat line) for
    Prophet's fit to converge normally.
    """
    rng = np.random.default_rng(seed=42)
    dates = pd.date_range("2024-01-01", periods=n_rows, freq="D")
    trend = np.linspace(100, 130, n_rows)
    noise = rng.normal(0, 1.5, n_rows)
    values = trend + noise
    return pd.Series(values, index=dates)


def test_forecast_forward_returns_forecast_and_ci_of_correct_length():
    close = _synthetic_close()
    horizon_days = 7

    result = prophet_model.forecast_forward(close, horizon_days)

    assert set(result.keys()) == {"forecast", "ci_lower", "ci_upper"}
    assert len(result["forecast"]) == horizon_days
    assert len(result["ci_lower"]) == horizon_days
    assert len(result["ci_upper"]) == horizon_days


def test_forecast_forward_ci_lower_le_forecast_le_ci_upper():
    close = _synthetic_close()
    horizon_days = 7

    result = prophet_model.forecast_forward(close, horizon_days)

    for i in range(horizon_days):
        assert result["ci_lower"][i] <= result["forecast"][i] <= result["ci_upper"][i]


def test_forecast_forward_raises_runtime_error_when_prophet_unavailable(monkeypatch):
    monkeypatch.setattr(prophet_model, "PROPHET_AVAILABLE", False)
    close = _synthetic_close(n_rows=10)

    try:
        prophet_model.forecast_forward(close, horizon_days=7)
        assert False, "expected RuntimeError to be raised"
    except RuntimeError as exc:
        assert "prophet" in str(exc).lower() or "Prophet" in str(exc)


def test_interval_width_is_80_percent():
    assert prophet_model.INTERVAL_WIDTH == 0.80
