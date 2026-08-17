"""Zero-I/O forecast+backtest dispatch orchestrator (PRED-02/PRED-03).

``generate_forecast`` is the single validated, exception-safe dispatch
point Plan 08/09's page code calls -- it never lets a page import a model
module or ``backtest.py`` directly (single-entry-point pattern, mirroring
``src.recommendation.engine``'s ``score_universe``). It is the single
place ``model``/``horizon_days`` input validation happens (T-04-05) and
the single place a Prophet-unavailable or any other failure degrades to a
predictable status dict instead of crashing.

Note this module's "zero I/O" contract is identical in *kind* to
``src.recommendation.engine``'s: XGBoost/Prophet training happens
in-process on CPU, which still counts as "zero I/O" for this convention's
purposes since no network, database, or LLM call occurs anywhere in this
module or its sibling ``src.prediction`` modules.

``generate_forecast`` composes sibling modules' outputs -- it never
reimplements ``backtest.run_backtest``'s metrics math or any model's
``forecast_forward`` path math inline (Composition-not-reimplementation
convention, 04-PATTERNS.md).

This module performs zero network, database, or LLM calls. It imports
only ``logging``, ``pandas``, and sibling ``src.prediction`` modules --
never ``streamlit``, ``yfinance``, or ``sqlite3``.
"""

import logging

import pandas as pd

from src.prediction import backtest, prophet_model, sma_model, xgboost_model

logger = logging.getLogger(__name__)

VALID_MODELS = {"sma", "xgboost", "prophet"}
VALID_HORIZONS = {7, 30, 90}

# Exact strings matching 04-UI-SPEC.md's Copywriting Contract, in this
# fixed insertion order -- Plan 08/09's dropdown/compare-view iteration
# order depends on this dict's insertion order, never re-sorted.
MODEL_LABELS = {
    "sma": "SMA Baseline",
    "xgboost": "XGBoost",
    "prophet": "Prophet",
}


def _forecast_forward_dispatch(
    model_name: str,
    feature_frame: pd.DataFrame,
    price_series: pd.Series,
    horizon_days: int,
) -> dict:
    """Dispatch to the named model's live forward forecast (never a
    backtest fold) -- returns its ``{"forecast", "ci_lower", "ci_upper"}``
    dict unchanged."""
    if model_name == "sma":
        return sma_model.forecast_forward(price_series, horizon_days)
    if model_name == "xgboost":
        return xgboost_model.forecast_forward(feature_frame, price_series, horizon_days)
    return prophet_model.forecast_forward(price_series, horizon_days)


def _build_forecast_index(last_date, horizon_days: int) -> pd.DatetimeIndex:
    """Applied uniformly regardless of which model produced the forecast,
    so the chart x-axis stays consistent across model switches."""
    return pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon_days, freq="D")


def generate_forecast(
    ticker: str,
    model: str,
    horizon_days: int,
    feature_frame: pd.DataFrame,
    price_series: pd.Series,
    asset_class: str,
) -> dict:
    """Validate ``model``/``horizon_days``, then compose a backtest
    (``backtest.run_backtest``) and a live forward forecast (the named
    model's ``forecast_forward``) into one caller-facing result dict.

    Never trusts a caller-supplied ``model``/``horizon_days`` without
    independent validation, even though Plan 08's UI constrains these via
    closed-set ``st.selectbox`` widgets -- ``generate_forecast`` is a
    plain Python function callable with any string/int (T-04-05).

    Returns on success: ``{"status": "ok", "ticker": ..., "model": ...,
    "horizon_days": ..., "forecast_index": <DatetimeIndex>, "forecast":
    <ndarray>, "ci_lower": <ndarray>, "ci_upper": <ndarray>,
    "backtest_metrics": <dict>}``.

    Returns ``{"status": "prophet_unavailable"}`` when ``model ==
    "prophet"`` and ``prophet_model.PROPHET_AVAILABLE`` is ``False`` --
    checked before any backtest/forecast work is attempted.

    Returns ``{"status": "error"}`` (never raises) if
    ``backtest.run_backtest`` or the dispatched model's
    ``forecast_forward`` raises any exception -- logged via
    ``logger.exception`` first (T-04-06).

    Raises:
        ValueError: if ``model`` is not in ``VALID_MODELS`` or
            ``horizon_days`` is not in ``VALID_HORIZONS`` -- raised before
            any dispatch, backtest, or forecast work happens.
    """
    if model not in VALID_MODELS:
        raise ValueError(f"model must be one of {sorted(VALID_MODELS)}, got {model!r}")
    if horizon_days not in VALID_HORIZONS:
        raise ValueError(
            f"horizon_days must be one of {sorted(VALID_HORIZONS)}, got {horizon_days!r}"
        )

    if model == "prophet" and not prophet_model.PROPHET_AVAILABLE:
        return {"status": "prophet_unavailable"}

    try:
        backtest_metrics = backtest.run_backtest(
            model, feature_frame, price_series, horizon_days, asset_class
        )
        forward = _forecast_forward_dispatch(model, feature_frame, price_series, horizon_days)
        forecast_index = _build_forecast_index(price_series.index[-1], horizon_days)

        return {
            "status": "ok",
            "ticker": ticker,
            "model": model,
            "horizon_days": horizon_days,
            "forecast_index": forecast_index,
            "forecast": forward["forecast"],
            "ci_lower": forward["ci_lower"],
            "ci_upper": forward["ci_upper"],
            "backtest_metrics": backtest_metrics,
        }
    except Exception:
        logger.exception(
            "generate_forecast failed for %s/%s/%s", ticker, model, horizon_days
        )
        return {"status": "error"}
