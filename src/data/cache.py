"""Single yfinance chokepoint for the whole codebase (D-07/D-08/D-09).

``fetch_ohlcv()`` is layered: ``st.cache_data(ttl=CACHE_TTL_SECONDS)`` ->
SQLite disk cache (survives a cold container after Streamlit Cloud sleep,
per D-07) -> ``tenacity``-wrapped live fetch -> write-through to both layers
on success, fall back to a stale SQLite row + a "stale" status flag on
failure (D-09). No other module in this codebase may import ``yfinance``
directly -- ``src/data/prices.py`` re-exports this function as the only
cross-module entry point for price data (RESEARCH.md Pattern 3).
"""

import io
import sqlite3
import time
from typing import Optional, Tuple

import pandas as pd
import streamlit as st
import yfinance as yf
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config import CACHE_TTL_SECONDS

# Local disk cache path. Purely a performance optimization with no
# durability guarantee across redeploys (Pitfall 4) -- callers must not
# assume this file exists on a fresh checkout.
DB_PATH = "data/price_cache.db"


def _init_db() -> None:
    """Create the price_cache table if it does not already exist."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS price_cache (
                ticker TEXT,
                period TEXT,
                fetched_at REAL,
                payload_json TEXT,
                PRIMARY KEY (ticker, period)
            )
            """
        )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _fetch_live(ticker: str, period: str) -> pd.DataFrame:
    """Live yfinance fetch, retried up to 3 times with exponential backoff.

    A single bulk ``yf.download()`` call -- never a per-ticker loop
    (Pitfall 6). No specific requests-per-minute constant is hardcoded here;
    Yahoo publishes no documented rate-limit numbers for this endpoint, so
    retry-on-failure plus the cache-first architecture above is the whole
    mitigation. ``reraise=True`` so a total failure surfaces as the original
    exception type, not tenacity's own wrapping ``RetryError``.
    """
    return yf.download(ticker, period=period, progress=False)


def _write_through(ticker: str, period: str, df: pd.DataFrame) -> None:
    """Write-through a freshly fetched DataFrame to the SQLite disk cache.

    Every value is passed as a bound parameter (``?`` placeholders) -- the
    ticker/period strings are never interpolated directly into the SQL text
    (T-01-03).
    """
    payload_json = df.to_json(orient="split", date_format="iso")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO price_cache (ticker, period, fetched_at, payload_json) "
            "VALUES (?, ?, ?, ?)",
            (ticker, period, time.time(), payload_json),
        )


def _read_disk_cache(ticker: str, period: str) -> Optional[Tuple[pd.DataFrame, float]]:
    """Read a previously write-through-cached row, if one exists.

    Returns ``None`` if no row exists for this ticker/period. Uses ``?``
    placeholders exclusively (T-01-03).
    """
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT fetched_at, payload_json FROM price_cache WHERE ticker = ? AND period = ?",
            (ticker, period),
        ).fetchone()

    if row is None:
        return None

    fetched_at, payload_json = row
    df = pd.read_json(io.StringIO(payload_json), orient="split")
    return df, fetched_at


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_ohlcv(ticker: str, period: str = "1y") -> Tuple[pd.DataFrame, str]:
    """Fetch OHLCV data for ``ticker`` over ``period``.

    Returns ``(DataFrame, status)`` where ``status`` is ``"live"`` on a
    fresh fetch, or ``"stale"`` when falling back to a previously
    write-through-cached disk row after a live-fetch failure. When the live
    fetch fails and no cached row exists at all, the original exception is
    re-raised -- a genuine total failure surfaces loudly rather than
    returning ``None`` or an empty DataFrame silently (Pitfall 4).
    """
    _init_db()
    try:
        df = _fetch_live(ticker, period)
        _write_through(ticker, period, df)
        return df, "live"
    except Exception:
        cached = _read_disk_cache(ticker, period)
        if cached is not None:
            stale_df, _fetched_at = cached
            return stale_df, "stale"
        raise


def format_stale_cache_message(fetched_at) -> str:
    """Render the exact UI-SPEC Copywriting Contract sentence for the
    stale/degraded price-data state (D-09), for a later phase's
    price-display page to render.

    ``fetched_at`` is substituted in as-is -- this function does no
    timestamp formatting of its own, only the fixed-template substitution.
    """
    return f"Showing saved data from {fetched_at} — live prices are temporarily unavailable."
