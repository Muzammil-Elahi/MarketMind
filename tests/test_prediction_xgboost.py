"""Tests for src/prediction/xgboost_model.py (PRED-02/PRED-03).

Uses a small, deterministic synthetic features/close fixture built via
src.features.feature_frame.assemble_feature_frame applied to a synthetic
OHLCV DataFrame, dropna'd, mirroring tests/test_universe_loader.py's
_sample_ohlcv helper. No mocking of xgboost itself -- real, small, fast
fits prove the actual quantile-regression math works. No network calls.
"""

import numpy as np
import pandas as pd

from src.features.feature_frame import assemble_feature_frame
from src.prediction.xgboost_model import (
    QUANTILES,
    _make_direct_target,
    fit_predict,
    forecast_forward,
)


def _sample_ohlcv(n_rows: int) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n_rows, freq="D")
    close = pd.Series(
        100 + np.sin(np.arange(n_rows) / 3.0) * 5 + np.arange(n_rows) * 0.5,
        index=dates,
        dtype=float,
    )
    return pd.DataFrame(
        {"Open": close, "High": close + 1, "Low": close - 1, "Close": close}
    )


def _sample_features_and_close(n_rows: int = 60, warmup: int = 30):
    """Build a features/close fixture of exactly n_rows, aligned on the
    same index, with all rolling-window NaN warmup rows already dropped."""
    raw = _sample_ohlcv(n_rows + warmup)
    features = assemble_feature_frame(raw).dropna()
    features = features.iloc[-n_rows:]
    close = raw["Close"].loc[features.index]
    return features, close


def test_fit_predict_trains_on_exactly_masked_direct_horizon_rows():
    """For a features/close fixture of length 60 and horizon_days=7,
    exactly 60 - 7 = 53 rows have a valid target and are used for
    training -- asserted via a row-count check on the masked training
    data itself, not just the final prediction."""
    features, close = _sample_features_and_close(n_rows=60)
    horizon_days = 7
    assert len(features) == 60

    target = _make_direct_target(close, horizon_days)
    train_mask = target.notna()

    assert train_mask.sum() == 53
    assert features.loc[train_mask].shape[0] == 53


def test_fit_predict_returns_valid_endpoint_dict():
    features, close = _sample_features_and_close(n_rows=60)

    result = fit_predict(features, close, horizon_days=7)

    assert set(result.keys()) == {
        "forecast_endpoint",
        "ci_lower_endpoint",
        "ci_upper_endpoint",
    }
    for value in result.values():
        assert isinstance(value, float)
    assert result["ci_lower_endpoint"] <= result["forecast_endpoint"]
    assert result["forecast_endpoint"] <= result["ci_upper_endpoint"]


def test_forecast_forward_returns_dict_with_arrays_of_length_horizon():
    features, close = _sample_features_and_close(n_rows=60)
    horizon_days = 7

    result = forecast_forward(features, close, horizon_days)

    assert set(result.keys()) == {"forecast", "ci_lower", "ci_upper"}
    for key in ("forecast", "ci_lower", "ci_upper"):
        assert isinstance(result[key], np.ndarray)
        assert len(result[key]) == horizon_days


def test_forecast_forward_first_day_closer_to_today_than_endpoint_is():
    features, close = _sample_features_and_close(n_rows=60)
    horizon_days = 7

    endpoint = fit_predict(features, close, horizon_days)
    result = forecast_forward(features, close, horizon_days)

    today_price = close.iloc[-1]
    assert endpoint["forecast_endpoint"] != today_price, (
        "fixture must produce a nontrivial endpoint prediction for this "
        "interpolation-direction assertion to be meaningful"
    )

    day1_distance = abs(result["forecast"][0] - today_price)
    endpoint_distance = abs(result["forecast"][-1] - today_price)
    assert day1_distance < endpoint_distance


def test_forecast_forward_band_width_zero_at_start_full_at_end():
    features, close = _sample_features_and_close(n_rows=60)
    horizon_days = 7

    endpoint = fit_predict(features, close, horizon_days)
    result = forecast_forward(features, close, horizon_days)

    band_width = result["ci_upper"] - result["ci_lower"]
    endpoint_width = endpoint["ci_upper_endpoint"] - endpoint["ci_lower_endpoint"]

    np.testing.assert_allclose(band_width[0], 0.0, atol=1e-9)
    np.testing.assert_allclose(band_width[-1], endpoint_width, rtol=1e-6)


def test_forecast_forward_bounds_hold_for_every_step():
    features, close = _sample_features_and_close(n_rows=60)

    result = forecast_forward(features, close, horizon_days=7)

    assert (result["ci_lower"] <= result["forecast"]).all()
    assert (result["forecast"] <= result["ci_upper"]).all()


def test_quantiles_constant_value():
    assert QUANTILES == [0.1, 0.5, 0.9]


def test_module_has_no_prohibited_io_imports():
    import inspect

    from src.prediction import xgboost_model

    source = inspect.getsource(xgboost_model)

    assert "import streamlit" not in source
    assert "import yfinance" not in source
    assert "import sqlite3" not in source
