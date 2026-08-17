"""Zero-I/O walk-forward backtest orchestrator (PRED-04, second half of
the no-lookahead-bias guarantee -- Plan 03's ``walk_forward.make_folds``
built the structural fold-generation half; this module proves no model
ever sees a test fold's own data during that fold's fit call).

``run_backtest`` is the single shared per-fold evaluation loop every
model uses (Plan 08's ``engine.generate_forecast`` is the only caller) --
it never reimplements ``walk_forward``/``metrics`` math inline, only
composes their outputs (Composition-not-reimplementation convention,
04-PATTERNS.md).

Per-fold signal-following return construction (``captured_returns``): for
each fold, ``predicted_direction`` is the sign of the model's predicted
change from that fold's last training price to its predicted horizon
endpoint, and ``captured_returns`` is that direction multiplied by the
*actual* realized return over the same fold window
(``actual_endpoint / actual_start - 1``). This is a small (``N_FOLDS``-
length) descriptive backtest statistic feeding ``metrics.sharpe_ratio`` --
it is never a trading instruction, a guarantee of future performance, or
literally executed anywhere in this codebase (04-RESEARCH.md Assumption
A-05; COMPLY-02-adjacent framing carried through to Plan 08's "Sharpe
Ratio (Simulated)" UI label).

This module performs zero network, database, or LLM calls. It imports
only ``numpy``, ``pandas``, and sibling ``src.prediction`` modules --
never ``streamlit``, ``yfinance``, or ``sqlite3``.
"""

import numpy as np
import pandas as pd

from src.prediction import metrics, prophet_model, sma_model, xgboost_model
from src.prediction.walk_forward import make_folds


def _sma_endpoint(features: pd.DataFrame, close: pd.Series, horizon_days: int) -> float:
    return float(sma_model.forecast_forward(close, horizon_days)["forecast"][-1])


def _xgboost_endpoint(
    features: pd.DataFrame, close: pd.Series, horizon_days: int
) -> float:
    return float(xgboost_model.fit_predict(features, close, horizon_days)["forecast_endpoint"])


def _prophet_endpoint(
    features: pd.DataFrame, close: pd.Series, horizon_days: int
) -> float:
    return float(prophet_model.forecast_forward(close, horizon_days)["forecast"][-1])


# Each entry shares one call signature -- (features, close, horizon_days)
# -- regardless of whether the model actually uses `features` (SMA/Prophet
# ignore it), so run_backtest's per-fold loop below never branches on
# model_name beyond this single dict lookup.
MODEL_ENDPOINT_FNS: dict[str, callable] = {
    "sma": _sma_endpoint,
    "xgboost": _xgboost_endpoint,
    "prophet": _prophet_endpoint,
}


def run_backtest(
    model_name: str,
    feature_frame: pd.DataFrame,
    price_series: pd.Series,
    horizon_days: int,
    asset_class: str,
) -> dict:
    """Evaluate ``model_name`` across ``walk_forward.make_folds``'s
    expanding-window folds, fitting each fold strictly on that fold's own
    ``train_index`` slice of ``feature_frame``/``price_series`` -- never
    the full history, and never a slice that includes any row from that
    fold's own ``test_index`` (PRED-04).

    Never calls ``src.features.feature_frame.assemble_feature_frame``
    itself -- it only slices the already-assembled ``feature_frame`` it
    receives by fold index (assembling features per-fold would silently
    shrink the rolling-window warm-up period differently per fold,
    04-RESEARCH.md Anti-Pattern).

    Returns ``{"rmse": float, "directional_accuracy": float, "sharpe":
    float}``.

    Raises:
        RuntimeError: if ``model_name == "prophet"`` and
            ``prophet_model.PROPHET_AVAILABLE`` is ``False`` -- raised
            immediately, before ``make_folds`` is ever called, so a
            Prophet-unavailable backtest never runs any fold work.
            ``engine.py`` is responsible for catching this before it
            reaches a user-facing error.
    """
    if model_name == "prophet" and not prophet_model.PROPHET_AVAILABLE:
        raise RuntimeError("Prophet is not available in this environment")

    endpoint_fn = MODEL_ENDPOINT_FNS[model_name]
    folds = make_folds(len(price_series), horizon_days)

    predicted_endpoints = []
    actual_endpoints = []
    actual_starts = []

    for train_index, test_index in folds:
        train_features = feature_frame.iloc[train_index]
        train_close = price_series.iloc[train_index]

        predicted_endpoint = endpoint_fn(train_features, train_close, horizon_days)
        actual_endpoint = float(price_series.iloc[test_index[-1]])
        actual_start = float(price_series.iloc[train_index[-1]])

        predicted_endpoints.append(predicted_endpoint)
        actual_endpoints.append(actual_endpoint)
        actual_starts.append(actual_start)

    predicted_endpoints = np.array(predicted_endpoints)
    actual_endpoints = np.array(actual_endpoints)
    actual_starts = np.array(actual_starts)

    predicted_direction = np.sign(predicted_endpoints - actual_starts)
    actual_direction = np.sign(actual_endpoints - actual_starts)

    # Guard against division-by-zero (WR-04): a literal-zero actual_start
    # (bad upstream data) would otherwise silently poison captured_returns
    # with inf/NaN and propagate into metrics.sharpe_ratio's mean/std --
    # matching this module's own metrics.sharpe_ratio `std == 0 -> 0.0`
    # zero-division guard convention (and
    # src/recommendation/similarity.py's cosine_similarity zero-vector
    # guard) rather than leaving this division unguarded. Folds with a
    # zero actual_start contribute 0.0 (no signal) instead of inf/NaN.
    safe_starts = np.where(actual_starts == 0, np.nan, actual_starts)
    with np.errstate(invalid="ignore"):
        fold_returns = actual_endpoints / safe_starts - 1
    captured_returns = np.nan_to_num(predicted_direction * fold_returns, nan=0.0)

    return {
        "rmse": metrics.rmse(predicted_endpoints, actual_endpoints),
        "directional_accuracy": metrics.directional_accuracy(
            predicted_direction, actual_direction
        ),
        "sharpe": metrics.sharpe_ratio(captured_returns, asset_class, horizon_days),
    }
