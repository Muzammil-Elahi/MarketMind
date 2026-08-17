"""Zero-I/O shared backtest metrics module (PRED-04, D-06's apples-to-
apples "Compare all models" requirement).

Every model's backtest evaluation (Plans 04/05/06) calls these shared
RMSE/directional-accuracy/Sharpe formulas rather than each implementing
its own -- eliminating the risk of divergent per-model metric formulas
and centralizing the asset-class-aware Sharpe annualization Pitfall 5
flags as an easy place to silently get wrong.

This module performs zero network, database, or LLM calls. It imports
only ``numpy`` and the standard library -- never ``streamlit``,
``yfinance``, or ``sqlite3``.
"""

import math

import numpy as np

# Crypto trades 7 days/week (~365 data points/year); everything else
# (stocks, ETFs, gold futures, forex) uses the standard ~252 trading-day
# calendar -- 04-RESEARCH.md Pitfall 5.
TRADING_DAYS_PER_YEAR = {"crypto": 365}
DEFAULT_TRADING_DAYS_PER_YEAR = 252  # stocks, ETFs, gold futures, forex


def rmse(predicted: np.ndarray, actual: np.ndarray) -> float:
    """Root-mean-squared error between predicted and actual values."""
    return float(np.sqrt(np.mean((predicted - actual) ** 2)))


def directional_accuracy(
    predicted_direction: np.ndarray, actual_direction: np.ndarray
) -> float:
    """Fraction of elements where predicted and actual direction/sign
    match. Both arrays are +1/-1 (or 0 for no-change) sign arrays of price
    change over each backtest fold's horizon."""
    return float(np.mean(predicted_direction == actual_direction))


def sharpe_ratio(
    captured_returns: np.ndarray, asset_class: str, horizon_days: int
) -> float:
    """Annualized Sharpe ratio of a signal-following long/short strategy
    driven by this model's predicted direction each backtest fold.

    ``captured_returns`` is a small (``N_FOLDS``-length, i.e. 5-element)
    array of per-fold signal-following realized returns, not daily
    returns -- a documented v1 simplification (04-RESEARCH.md Assumptions
    Log A-05). Each element is realized over ``horizon_days`` (the
    backtest's selected forecast horizon), not over one trading day, so
    the annualization factor must be scaled by how many ``horizon_days``-
    length periods fit in a year (``periods_per_year / horizon_days``) --
    never a flat ``periods_per_year`` treated as if returns were daily
    (WR-02): that would overstate the annualized figure, and by a
    different amount at each horizon, making the metric incomparable
    across the horizon selector. This value is a descriptive backtest
    statistic only, never a guarantee or trading instruction
    (COMPLY-02-adjacent framing carried through to the UI layer in Plan
    08's "Sharpe Ratio (Simulated)" label).

    Guarded against division-by-zero: returns 0.0 (never NaN/inf, never
    raises) when captured_returns.std() == 0, matching
    src/recommendation/similarity.py's cosine_similarity zero-vector guard
    convention.
    """
    periods_per_year = TRADING_DAYS_PER_YEAR.get(
        asset_class, DEFAULT_TRADING_DAYS_PER_YEAR
    )
    std = captured_returns.std()
    if std == 0:
        return 0.0
    periods_per_year_at_horizon = periods_per_year / horizon_days
    return float(captured_returns.mean() / std * np.sqrt(periods_per_year_at_horizon))


def _round_half_up(value: float, decimals: int) -> float:
    """Round-half-up to a fixed number of decimals -- never Python's
    built-in ``round()``, which is banker's-rounding and would silently
    round financial-looking numbers shown to users the wrong way (e.g.
    61.25 -> 61.2 instead of 61.3). Generalizes
    src/recommendation/engine.py's integer-only ``_round_half_up``."""
    factor = 10**decimals
    return math.floor(value * factor + 0.5) / factor


def format_metrics_for_display(backtest_metrics: dict) -> dict[str, str]:
    """Return display-ready strings for rmse/directional_accuracy/sharpe,
    using round-half-up rounding at a fixed, documented decimal precision
    -- matching REC-02's existing _round_half_up precedent for financial-
    looking numbers shown to users."""
    return {
        "rmse": f"{_round_half_up(backtest_metrics['rmse'], 2):.2f}",
        "directional_accuracy": (
            f"{_round_half_up(backtest_metrics['directional_accuracy'] * 100, 1):.1f}%"
        ),
        "sharpe": f"{_round_half_up(backtest_metrics['sharpe'], 2):.2f}",
    }
