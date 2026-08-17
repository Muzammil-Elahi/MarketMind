"""XGBoost direct-horizon quantile regression forecast model.

Pure, zero-I/O module (mirrors ``src/features/technical.py``'s module-
boundary discipline): every function takes an already-computed
``features`` DataFrame and ``close`` price Series and returns plain
floats/numpy arrays -- no ``streamlit``, ``yfinance``, or ``sqlite3``
import, no network call, no disk access anywhere in this file.

Trains on a *direct-horizon* target (``close.shift(-horizon_days)``) --
never a recursive one-step-ahead loop fed back in as input for the next
step, which compounds tree-model error and cannot extrapolate outside
the training distribution (04-RESEARCH.md Anti-Pattern).

Source: XGBoost official docs, Quantile Regression example
(https://xgboost.readthedocs.io/en/stable/python/examples/quantile_regression.html)
-- see 04-RESEARCH.md Pattern 3.
"""

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

QUANTILES = [0.1, 0.5, 0.9]


def _make_direct_target(close: pd.Series, horizon_days: int) -> pd.Series:
    """Target = close price ``horizon_days`` in the future.

    Rows near the end of history have no valid target and must be
    dropped before training (they are exactly the rows the live forward
    forecast predicts for).
    """
    return close.shift(-horizon_days)


def fit_predict(features: pd.DataFrame, close: pd.Series, horizon_days: int) -> dict:
    """Train 3 direct-horizon quantile XGBRegressor models and predict the
    single horizon-endpoint price + confidence interval.

    Trains at quantile_alpha 0.1/0.5/0.9 on a direct-horizon target
    (``close.shift(-horizon_days)``), never a recursive one-step-ahead
    loop. Rows with a NaN target (the tail of history) are dropped before
    fitting.
    """
    target = _make_direct_target(close, horizon_days)
    train_mask = target.notna()
    X_train, y_train = features.loc[train_mask], target.loc[train_mask]

    models = {}
    for q in QUANTILES:
        model = XGBRegressor(
            objective="reg:quantileerror",
            quantile_alpha=q,
            tree_method="hist",
            n_estimators=200,
        )
        model.fit(X_train, y_train)
        models[q] = model

    # Live forward forecast: predict off the most recent feature row (no
    # target exists for it yet -- that's the point).
    latest_row = features.iloc[[-1]]
    return {
        "forecast_endpoint": float(models[0.5].predict(latest_row)[0]),
        "ci_lower_endpoint": float(models[0.1].predict(latest_row)[0]),
        "ci_upper_endpoint": float(models[0.9].predict(latest_row)[0]),
    }


def forecast_forward(features: pd.DataFrame, close: pd.Series, horizon_days: int) -> dict:
    """Expose the same {"forecast", "ci_lower", "ci_upper"} path-shaped
    dict interface as sma_model.forecast_forward.

    Calls ``fit_predict`` exactly once per invocation to get the single
    horizon-endpoint prediction, then linearly interpolates it into a
    day-by-day path between today's price (t=0) and the endpoint
    (t=horizon_days), with the CI band width scaled by
    sqrt(t / horizon_days) between a zero-width band at t=0 and the full
    quantile-derived width at t=horizon_days (04-RESEARCH.md Pattern 3
    Design Note, A-03).
    """
    endpoint = fit_predict(features, close, horizon_days)

    last_price = close.iloc[-1]
    days = np.arange(1, horizon_days + 1)
    t_fraction = days / horizon_days

    forecast_path = last_price + (endpoint["forecast_endpoint"] - last_price) * t_fraction
    endpoint_width = endpoint["ci_upper_endpoint"] - endpoint["ci_lower_endpoint"]
    width_at_t = endpoint_width * np.sqrt(t_fraction)

    return {
        "forecast": forecast_path,
        "ci_lower": forecast_path - width_at_t / 2,
        "ci_upper": forecast_path + width_at_t / 2,
    }
