"""Shared synthetic feature_frame/price_series fixture builder for
src/prediction/ tests (Plan 06's backtest/engine/CI-invariant test suites).

Mirrors tests/test_prediction_xgboost.py's ``_sample_features_and_close``
helper -- extracted here as a single shared, importable helper so
``tests/test_prediction_backtest.py`` and ``tests/test_prediction_ci.py``
never duplicate the synthetic OHLCV construction independently
(04-PATTERNS.md composition-not-duplication convention, applied to test
fixtures too). Mirrors ``tests/test_universe_loader.py``'s ``_sample_ohlcv``
helper for the raw OHLCV shape.

Not itself a test file (no ``test_`` prefix) -- pytest never collects it
directly.
"""

import numpy as np
import pandas as pd

from src.features.feature_frame import assemble_feature_frame

# 252 (one trading year) + 5 * 7 (N_FOLDS * the smallest horizon_days,
# per walk_forward.py's MIN_PREDICTION_HISTORY_ROWS derivation) = 287, the
# Plan 03 arithmetic minimum for a horizon_days=7 backtest to have enough
# rows for all 5 folds. Default fixture size sits comfortably above that
# floor.
MIN_BACKTEST_FIXTURE_ROWS = 287
DEFAULT_FIXTURE_ROWS = 300


def sample_ohlcv(n_rows: int) -> pd.DataFrame:
    """A small, deterministic (fixed-seed) synthetic OHLCV DataFrame
    (sinusoidal wiggle + a mild upward trend + a little i.i.d. noise) on
    top of tests/test_universe_loader.py's/tests/test_prediction_xgboost.py's
    ``_sample_ohlcv`` shape.

    The added noise (mirroring tests/test_prediction_prophet.py's
    ``_synthetic_close`` helper) gives Prophet's residual-based
    uncertainty estimate nonzero variance to work with -- without it,
    Prophet's forecast-band width across a short (7-day) horizon can land
    within stochastic MCMC-sampling noise of a flat line, making the
    CI-band-widens-with-horizon invariant (PRED-03) an unreliable coin
    flip rather than a genuine, reproducible property of this fixture.
    """
    rng = np.random.default_rng(seed=42)
    dates = pd.date_range("2020-01-01", periods=n_rows, freq="D")
    noise = rng.normal(0, 0.3, n_rows)
    close = pd.Series(
        100 + np.sin(np.arange(n_rows) / 3.0) * 5 + np.arange(n_rows) * 0.05 + noise,
        index=dates,
        dtype=float,
    )
    return pd.DataFrame(
        {"Open": close, "High": close + 1, "Low": close - 1, "Close": close}
    )


def sample_feature_frame_and_price_series(
    n_rows: int = DEFAULT_FIXTURE_ROWS, warmup: int = 30
):
    """Build an aligned ``(feature_frame, price_series)`` pair of exactly
    ``n_rows``, with all rolling-window NaN warmup rows already dropped --
    exactly mirroring how Plan 07's ``_prediction_loader.py`` will
    construct these two objects for a live drill-in page."""
    raw = sample_ohlcv(n_rows + warmup)
    feature_frame = assemble_feature_frame(raw).dropna()
    feature_frame = feature_frame.iloc[-n_rows:]
    price_series = raw["Close"].loc[feature_frame.index]
    return feature_frame, price_series
