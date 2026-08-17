"""SMA baseline forecast model: random-walk-with-drift + square-root-of-time
confidence interval.

Pure, zero-I/O module (mirrors ``src/features/technical.py``'s module-
boundary discipline): every function takes an already-fetched ``close``
price ``pandas.Series`` and returns plain numpy arrays -- no
``streamlit``, ``yfinance``, or ``sqlite3`` import, no network call, no
disk access anywhere in this file.

Source: standard random-walk-with-drift forecasting formula (textbook
time-series pattern, e.g. Hyndman & Athanasopoulos "Forecasting:
Principles and Practice", ch. "Drift method") -- see 04-RESEARCH.md
Pattern 2.
"""

import numpy as np
import pandas as pd

Z_80PCT = 1.2816  # two-sided 80% CI z-score, matches Prophet's default
# interval_width=0.80 (Plan 05) so all three models' bands are visually
# comparable at the same confidence level (04-RESEARCH.md Assumption A-07).


def forecast_forward(close: pd.Series, horizon_days: int) -> dict:
    """Random-walk-with-drift forward forecast with an 80% confidence band.

    ``forecast[i]`` is the expected price ``i + 1`` days ahead, assuming
    the historical average daily return (``drift``) continues. The
    confidence band widens with ``sqrt(days)`` since the variance of a
    sum of i.i.d. daily returns grows linearly with the number of days
    (so its standard deviation grows with the square root of time).

    A perfectly flat ``close`` series (``sigma == 0``, PRED-03's
    zero-variance edge case) collapses the band to zero width at every
    step rather than raising or producing ``NaN`` -- ``sigma`` naturally
    evaluates to ``0.0`` in that case, so no special-casing is needed.
    """
    daily_returns = close.pct_change().dropna()
    drift = daily_returns.mean()
    sigma = daily_returns.std()

    last_price = close.iloc[-1]
    days = np.arange(1, horizon_days + 1)
    path = last_price * (1 + drift) ** days
    # sqrt(time) scaling: variance of a sum of i.i.d. daily returns grows
    # linearly with the number of days, so std grows with sqrt(days).
    band = last_price * sigma * np.sqrt(days) * Z_80PCT

    return {
        "forecast": path,
        "ci_lower": path - band,
        "ci_upper": path + band,
    }
