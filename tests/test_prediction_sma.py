"""Tests for src/prediction/sma_model.py (PRED-02/PRED-03).

All tests operate on small, deterministic synthetic ``close`` price
Series -- no mocking, no network, no Streamlit. sma_model.py is a pure,
zero-I/O module: these tests exercise that contract directly, following
tests/test_features_technical.py's synthetic-data style.
"""

import numpy as np
import pandas as pd

from src.prediction.sma_model import Z_80PCT, forecast_forward


def _constant_growth_close(n_rows: int = 30, daily_return: float = 0.005) -> pd.Series:
    """A close Series with a strictly positive constant daily return
    (every day +0.5% by default)."""
    dates = pd.date_range("2024-01-01", periods=n_rows, freq="D")
    values = 100.0 * (1 + daily_return) ** np.arange(n_rows)
    return pd.Series(values, index=dates, dtype=float)


def _flat_close(n_rows: int = 30, value: float = 100.0) -> pd.Series:
    """A perfectly flat close Series -- every value identical, sigma == 0."""
    dates = pd.date_range("2024-01-01", periods=n_rows, freq="D")
    return pd.Series([value] * n_rows, index=dates, dtype=float)


def _volatile_close(n_rows: int = 30) -> pd.Series:
    """A close Series with nonzero return volatility (sinusoidal wiggle on
    top of a mild upward trend), matching test_features_technical.py's
    _sample_ohlcv helper's shape."""
    dates = pd.date_range("2024-01-01", periods=n_rows, freq="D")
    values = 100 + np.sin(np.arange(n_rows) / 3.0) * 5 + np.arange(n_rows) * 0.5
    return pd.Series(values, index=dates, dtype=float)


def test_forecast_forward_returns_dict_with_arrays_of_length_horizon():
    close = _volatile_close()
    horizon_days = 7

    result = forecast_forward(close, horizon_days)

    assert set(result.keys()) == {"forecast", "ci_lower", "ci_upper"}
    for key in ("forecast", "ci_lower", "ci_upper"):
        assert isinstance(result[key], np.ndarray)
        assert len(result[key]) == horizon_days


def test_forecast_forward_is_strictly_increasing_for_positive_constant_drift():
    close = _constant_growth_close(daily_return=0.005)

    result = forecast_forward(close, horizon_days=7)

    forecast = result["forecast"]
    assert all(forecast[i] < forecast[i + 1] for i in range(len(forecast) - 1))


def test_forecast_forward_bounds_hold_for_every_step():
    close = _volatile_close()

    result = forecast_forward(close, horizon_days=7)

    assert (result["ci_lower"] <= result["forecast"]).all()
    assert (result["forecast"] <= result["ci_upper"]).all()


def test_forecast_forward_band_width_strictly_increases_with_volatility():
    close = _volatile_close()

    result = forecast_forward(close, horizon_days=7)

    band_width = result["ci_upper"] - result["ci_lower"]
    assert all(band_width[i] < band_width[i + 1] for i in range(len(band_width) - 1))


def test_forecast_forward_zero_variance_collapses_band_to_zero_width():
    close = _flat_close()

    result = forecast_forward(close, horizon_days=7)

    np.testing.assert_allclose(result["ci_lower"], result["forecast"])
    np.testing.assert_allclose(result["ci_upper"], result["forecast"])
    assert not np.isnan(result["forecast"]).any()
    assert not np.isnan(result["ci_lower"]).any()
    assert not np.isnan(result["ci_upper"]).any()


def test_z_80pct_constant_value():
    assert Z_80PCT == 1.2816


def test_module_has_no_prohibited_io_imports():
    import inspect

    from src.prediction import sma_model

    source = inspect.getsource(sma_model)

    assert "import streamlit" not in source
    assert "import yfinance" not in source
    assert "import sqlite3" not in source
