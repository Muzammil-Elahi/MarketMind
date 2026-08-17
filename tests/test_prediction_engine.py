"""Tests for src/prediction/engine.py (generate_forecast dispatch,
D-01-D-06, T-04-05 input validation, T-04-06 exception-safety).

Mirrors tests/test_ticker_validation.py's patch-the-imported-name
convention: mocks src.prediction.engine.backtest.run_backtest / the
relevant model's forecast_forward, never the real sibling modules
directly (except for the one real end-to-end "sma" call proving the
success-path shape). No network calls, no real prophet fit anywhere in
this file.
"""

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from src.prediction import prophet_model
from src.prediction.engine import (
    HORIZON_LABELS,
    MODEL_LABELS,
    VALID_HORIZONS,
    VALID_MODELS,
    generate_forecast,
)

# Bare top-level import -- see tests/test_prediction_backtest.py's comment
# on the globally installed unrelated `tests` PyPI package shadowing
# `tests.<module>` dotted imports in this environment.
from _prediction_fixtures import sample_feature_frame_and_price_series

TICKER = "AAPL"
HORIZON_DAYS = 7


def _fixture():
    return sample_feature_frame_and_price_series()


def test_valid_models_and_horizons_constants():
    assert VALID_MODELS == {"sma", "xgboost", "prophet"}
    assert VALID_HORIZONS == {7, 30, 90}


def test_model_labels_exact_strings_and_order():
    assert MODEL_LABELS == {
        "sma": "SMA Baseline",
        "xgboost": "XGBoost",
        "prophet": "Prophet",
    }
    assert list(MODEL_LABELS.keys()) == ["sma", "xgboost", "prophet"]


def test_horizon_labels_keys_match_valid_horizons_exactly():
    """WR-03: HORIZON_LABELS' keys must always equal VALID_HORIZONS exactly
    -- both now live in this module (single source of truth) specifically
    so they can never drift apart and trigger an uncaught KeyError in
    search.py's format_func at render time."""
    assert set(HORIZON_LABELS) == VALID_HORIZONS
    assert HORIZON_LABELS == {7: "7 Days", 30: "30 Days", 90: "90 Days"}


def test_generate_forecast_raises_value_error_for_invalid_model():
    feature_frame, price_series = _fixture()

    with patch("src.prediction.engine.backtest.run_backtest") as mock_run_backtest, patch(
        "src.prediction.engine.sma_model.forecast_forward"
    ) as mock_sma, patch(
        "src.prediction.engine.xgboost_model.forecast_forward"
    ) as mock_xgb, patch(
        "src.prediction.engine.prophet_model.forecast_forward"
    ) as mock_prophet:
        with pytest.raises(ValueError) as exc_info:
            generate_forecast(
                TICKER,
                "not-a-real-model",
                HORIZON_DAYS,
                feature_frame,
                price_series,
                "Stocks",
            )

    message = str(exc_info.value)
    assert "sma" in message
    assert "xgboost" in message
    assert "prophet" in message
    mock_run_backtest.assert_not_called()
    mock_sma.assert_not_called()
    mock_xgb.assert_not_called()
    mock_prophet.assert_not_called()


def test_generate_forecast_raises_value_error_for_invalid_horizon():
    feature_frame, price_series = _fixture()

    with patch("src.prediction.engine.backtest.run_backtest") as mock_run_backtest, patch(
        "src.prediction.engine.sma_model.forecast_forward"
    ) as mock_sma:
        with pytest.raises(ValueError) as exc_info:
            generate_forecast(TICKER, "sma", 15, feature_frame, price_series, "Stocks")

    message = str(exc_info.value)
    assert "7" in message
    assert "30" in message
    assert "90" in message
    mock_run_backtest.assert_not_called()
    mock_sma.assert_not_called()


def test_generate_forecast_returns_prophet_unavailable_status(monkeypatch):
    feature_frame, price_series = _fixture()
    monkeypatch.setattr(prophet_model, "PROPHET_AVAILABLE", False)

    with patch("src.prediction.engine.backtest.run_backtest") as mock_run_backtest:
        result = generate_forecast(
            TICKER, "prophet", HORIZON_DAYS, feature_frame, price_series, "Stocks"
        )

    assert result == {"status": "prophet_unavailable"}
    mock_run_backtest.assert_not_called()


def test_generate_forecast_ok_shape_for_real_sma_call():
    feature_frame, price_series = _fixture()

    result = generate_forecast(
        TICKER, "sma", HORIZON_DAYS, feature_frame, price_series, "Stocks"
    )

    assert result["status"] == "ok"
    assert result["ticker"] == TICKER
    assert result["model"] == "sma"
    assert result["horizon_days"] == HORIZON_DAYS
    assert isinstance(result["forecast_index"], pd.DatetimeIndex)
    assert len(result["forecast_index"]) == HORIZON_DAYS
    assert result["forecast_index"][0] == price_series.index[-1] + pd.Timedelta(days=1)
    for key in ("forecast", "ci_lower", "ci_upper"):
        assert isinstance(result[key], np.ndarray)
        assert len(result[key]) == HORIZON_DAYS
    assert set(result["backtest_metrics"].keys()) == {
        "rmse",
        "directional_accuracy",
        "sharpe",
    }


def test_generate_forecast_returns_error_status_on_exception_never_propagates():
    feature_frame, price_series = _fixture()

    with patch(
        "src.prediction.engine.backtest.run_backtest",
        side_effect=RuntimeError("boom"),
    ):
        result = generate_forecast(
            TICKER, "sma", HORIZON_DAYS, feature_frame, price_series, "Stocks"
        )

    assert result == {"status": "error"}


def test_module_has_no_prohibited_io_imports():
    import inspect

    from src.prediction import engine

    source = inspect.getsource(engine)

    assert "import streamlit" not in source
    assert "import yfinance" not in source
    assert "import sqlite3" not in source
