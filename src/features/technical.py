"""Pure, zero-I/O point-in-time technical/factor feature functions.

Every function here takes an already-fetched OHLCV ``DataFrame`` (as
returned by ``src.data.prices.fetch_ohlcv``, with capitalized columns —
``"Open"``/``"High"``/``"Low"``/``"Close"`` — matching yfinance's actual
output shape) and returns a ``pandas.Series`` aligned to ``df.index``.

Point-in-time safety (D-11, ROADMAP Phase 2 success criterion #3): every
rolling-window computation uses the non-centered default window alignment
(pandas' default) and never a negative-offset shift, so no function can
pull a future row into a value dated at or before today. A centered
rolling window is never used anywhere in this module — see 02-RESEARCH.md
Pattern 4 / Pitfall 4.

This module imports ``pandas`` and ``pandas_ta_classic`` only — no
``streamlit``, no ``yfinance``, no ``sqlite3``. It never fetches its own
data.
"""

import pandas as pd
import pandas_ta_classic as ta


def compute_returns(df: pd.DataFrame) -> pd.Series:
    """Simple percent-change return of the close price.

    Not a future-looking label — this is today's realized return given
    yesterday's close (``pct_change()`` never looks ahead).
    """
    return df["Close"].pct_change()


def compute_volatility(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Rolling standard deviation of returns over ``window`` bars.

    Uses a non-centered rolling window (``center=False``, pandas' default)
    — never a centered one, which would leak future rows into today's value.
    """
    return compute_returns(df).rolling(window, center=False).std()


def compute_sma(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Simple moving average of the close price over ``window`` bars.

    Calls ``pandas_ta_classic``'s functional API with a positional Series
    argument (``ta.sma(df["Close"], length=window)``) rather than the
    ``df.ta`` DataFrame accessor, to sidestep the accessor's column-name
    auto-detection ambiguity.
    """
    return ta.sma(df["Close"], length=window)


def compute_rsi(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Relative Strength Index of the close price over ``window`` bars.

    Every non-NaN value falls in the closed range [0, 100] by RSI's
    definition; the exact Wilder-smoothing computation is
    ``pandas_ta_classic``'s responsibility, not reimplemented here.
    """
    return ta.rsi(df["Close"], length=window)
