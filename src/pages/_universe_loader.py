"""Shared fetch + assemble + minimum-history gate for one asset (D-07/D-08).

Unlike ``src/recommendation/``, this module performs I/O -- it is
deliberately located under ``src/pages/`` rather than ``src/recommendation/``
for that reason. Both ``src/pages/recommendations.py`` (Plan 06) and
``src/pages/search.py`` (Plan 07) import from here rather than duplicating
the fetch-and-assemble loop.

``fetch_scorable_row`` distinguishes a D-07 "not found" outcome (the fetch
raised, or returned an empty DataFrame) from a D-08 "insufficient data"
outcome (the fetch succeeded but there isn't enough history to compute
reliable features) so callers can render the correct distinct UI state.
"""

import logging

import pandas as pd

from src.data.prices import fetch_ohlcv
from src.features.feature_frame import assemble_feature_frame
from src.recommendation.universe import MIN_HISTORY_ROWS

logger = logging.getLogger(__name__)


def fetch_scorable_row(
    ticker: str,
    asset_class: str,
    sector: str | None,
    ohlcv_df: pd.DataFrame | None = None,
) -> dict:
    """Fetch and assemble one asset's scorable feature row.

    ``ohlcv_df``, when provided, is an already-fetched OHLCV frame (e.g. a
    wider-period frame a caller such as the search page already fetched for
    another purpose) sliced to the trailing ~1 year of rows and used in
    place of a fresh ``fetch_ohlcv`` call -- this avoids a redundant live
    fetch for the same ticker (WR-01) while preserving this function's
    normal 1-year scoring/display window.

    Returns one of:
    - ``{"status": "not_found"}`` -- ``fetch_ohlcv`` raised, or returned an
      empty DataFrame (D-07).
    - ``{"status": "insufficient_data", "chart_df": df}`` -- the fetch
      succeeded with a non-empty ``df``, but the assembled, dropna'd
      feature frame has fewer than ``MIN_HISTORY_ROWS`` rows (D-08).
    - ``{"status": "ok", "chart_df": df, "feature_row": {...}}`` -- at
      least ``MIN_HISTORY_ROWS`` non-NaN feature rows exist; the numeric
      values in ``feature_row`` come from the most recent row of the
      dropna'd feature frame.
    """
    if ohlcv_df is not None:
        df = ohlcv_df
    else:
        try:
            df, _source = fetch_ohlcv(ticker)
        except Exception:
            logger.exception("fetch_scorable_row failed for %s", ticker)
            return {"status": "not_found"}

    if df.empty:
        return {"status": "not_found"}

    feature_frame = assemble_feature_frame(df).dropna()
    if len(feature_frame) < MIN_HISTORY_ROWS:
        return {"status": "insufficient_data", "chart_df": df}

    last_row = feature_frame.iloc[-1]
    return {
        "status": "ok",
        "chart_df": df,
        "feature_row": {
            "ticker": ticker,
            "asset_class": asset_class,
            "sector": sector,
            "returns": last_row["returns"],
            "volatility_20": last_row["volatility_20"],
            "rsi_14": last_row["rsi_14"],
        },
    }


def load_asset_feature_row(ticker: str, asset_class: str, sector: str | None) -> dict | None:
    """Thin wrapper over ``fetch_scorable_row`` -- returns the ``feature_row``
    dict when scorable, else ``None``.

    Coarser than ``fetch_scorable_row``: used by the recommendations page,
    which only needs scorable/unscorable, not the D-07/D-08 distinction.
    """
    result = fetch_scorable_row(ticker, asset_class, sector)
    if result["status"] == "ok":
        return result["feature_row"]
    return None


def load_universe_rows(
    tickers_with_metadata: list[tuple[str, str, str | None]],
) -> tuple[list[dict], list[str]]:
    """Load feature rows for a batch of (ticker, asset_class, sector) entries.

    Returns ``(scorable_rows, unscorable_tickers)`` -- one
    ``load_asset_feature_row`` call per entry.
    """
    scorable_rows: list[dict] = []
    unscorable_tickers: list[str] = []
    for ticker, asset_class, sector in tickers_with_metadata:
        feature_row = load_asset_feature_row(ticker, asset_class, sector)
        if feature_row is not None:
            scorable_rows.append(feature_row)
        else:
            unscorable_tickers.append(ticker)
    return scorable_rows, unscorable_tickers
