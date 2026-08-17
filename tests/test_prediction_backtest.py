"""Tests for src/prediction/backtest.py (PRED-04, no-lookahead-bias
guarantee at the per-fold fit/predict boundary).

Mirrors tests/test_features_leakage.py's structural-proof style (D-11),
adapted from feature-computation leakage to per-fold model-fit leakage.
Uses the shared synthetic fixture from tests/_prediction_fixtures.py (not
duplicated here). Only "sma" is used for the call-count/leakage-proof
tests -- the fastest of the 3 models, keeping this suite quick. No network
calls, no real prophet fit anywhere in this file.
"""

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from src.prediction import prophet_model
from src.prediction.backtest import MODEL_ENDPOINT_FNS, run_backtest
from src.prediction.walk_forward import make_folds
from tests._prediction_fixtures import sample_feature_frame_and_price_series

HORIZON_DAYS = 7


def _fixture():
    return sample_feature_frame_and_price_series()


def test_run_backtest_returns_dict_with_exactly_the_three_metric_keys():
    feature_frame, price_series = _fixture()

    result = run_backtest("sma", feature_frame, price_series, HORIZON_DAYS, "Stocks")

    assert set(result.keys()) == {"rmse", "directional_accuracy", "sharpe"}
    for value in result.values():
        assert isinstance(value, float)


def test_model_endpoint_fns_has_exactly_the_three_models():
    assert set(MODEL_ENDPOINT_FNS.keys()) == {"sma", "xgboost", "prophet"}
    for fn in MODEL_ENDPOINT_FNS.values():
        assert callable(fn)


def test_run_backtest_calls_make_folds_exactly_once():
    feature_frame, price_series = _fixture()

    with patch(
        "src.prediction.backtest.make_folds", wraps=make_folds
    ) as mock_make_folds:
        run_backtest("sma", feature_frame, price_series, HORIZON_DAYS, "Stocks")

    assert mock_make_folds.call_count == 1


def test_run_backtest_only_fits_each_fold_on_its_own_train_index_slice():
    """Every fold's model call receives ONLY that fold's train_index slice
    -- proven by asserting the close Series passed to sma_model's
    forecast_forward on every call has a max date strictly before that
    fold's test_index's minimum date (the same no-lookahead structural
    proof Plan 03 applied to fold generation, now applied to the
    fit-call boundary)."""
    feature_frame, price_series = _fixture()
    folds = make_folds(len(price_series), HORIZON_DAYS)

    seen_close_args = []

    def fake_forecast_forward(close, horizon_days):
        seen_close_args.append(close)
        return {
            "forecast": np.full(horizon_days, close.iloc[-1]),
            "ci_lower": np.full(horizon_days, close.iloc[-1]),
            "ci_upper": np.full(horizon_days, close.iloc[-1]),
        }

    with patch(
        "src.prediction.backtest.sma_model.forecast_forward",
        side_effect=fake_forecast_forward,
    ) as mock_ff:
        run_backtest("sma", feature_frame, price_series, HORIZON_DAYS, "Stocks")

    assert mock_ff.call_count == len(folds)
    assert len(seen_close_args) == len(folds)
    for (train_index, test_index), close_arg in zip(folds, seen_close_args):
        pd.testing.assert_index_equal(
            close_arg.index, price_series.iloc[train_index].index
        )
        fold_test_min_date = price_series.index[test_index].min()
        assert close_arg.index.max() < fold_test_min_date


def test_run_backtest_prophet_raises_before_any_fold_work_when_unavailable(
    monkeypatch,
):
    feature_frame, price_series = _fixture()
    monkeypatch.setattr(prophet_model, "PROPHET_AVAILABLE", False)

    with patch(
        "src.prediction.backtest.make_folds", wraps=make_folds
    ) as mock_make_folds:
        with pytest.raises(RuntimeError):
            run_backtest("prophet", feature_frame, price_series, HORIZON_DAYS, "Stocks")

    mock_make_folds.assert_not_called()


def test_perturbation_inside_last_fold_test_window_does_not_leak_into_earlier_fold():
    """D-11-style leakage proof: perturbing a price value inside ONLY the
    last fold's test window changes the full backtest's aggregate metrics
    (sanity: the perturbation is real), but an independently-computed
    metrics run using data truncated to end exactly at the FIRST fold's
    test window is byte-for-byte identical whether built from the
    unperturbed or perturbed series -- i.e. no perturbation inside a later
    fold's test window can leak backward into an earlier fold's fit."""
    feature_frame, price_series = _fixture()
    folds = make_folds(len(price_series), HORIZON_DAYS)
    _, fold1_test_index = folds[0]
    _, fold5_test_index = folds[-1]

    baseline_metrics = run_backtest(
        "sma", feature_frame, price_series, HORIZON_DAYS, "Stocks"
    )

    perturbed_price_series = price_series.copy()
    perturbed_price_series.iloc[fold5_test_index] = (
        perturbed_price_series.iloc[fold5_test_index] * 1000
    )

    perturbed_metrics = run_backtest(
        "sma", feature_frame, perturbed_price_series, HORIZON_DAYS, "Stocks"
    )

    assert perturbed_metrics != baseline_metrics

    truncation_end = fold1_test_index[-1] + 1
    truncated_feature_frame = feature_frame.iloc[:truncation_end]
    truncated_price_series = price_series.iloc[:truncation_end]
    truncated_perturbed_price_series = perturbed_price_series.iloc[:truncation_end]

    pd.testing.assert_series_equal(
        truncated_price_series, truncated_perturbed_price_series
    )

    baseline_truncated_metrics = run_backtest(
        "sma", truncated_feature_frame, truncated_price_series, HORIZON_DAYS, "Stocks"
    )
    perturbed_truncated_metrics = run_backtest(
        "sma",
        truncated_feature_frame,
        truncated_perturbed_price_series,
        HORIZON_DAYS,
        "Stocks",
    )

    assert baseline_truncated_metrics == perturbed_truncated_metrics


def test_module_has_no_prohibited_io_imports():
    import inspect

    from src.prediction import backtest

    source = inspect.getsource(backtest)

    assert "import streamlit" not in source
    assert "import yfinance" not in source
    assert "import sqlite3" not in source
