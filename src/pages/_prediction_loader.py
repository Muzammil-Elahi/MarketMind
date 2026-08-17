"""Fetch + assemble + minimum-history gate for one asset's prediction data
(D-07/D-08).

Unlike ``src/prediction/``, this module performs I/O -- it is deliberately
located under ``src/pages/`` rather than ``src/prediction/`` for that
reason, mirroring ``src/pages/_universe_loader.py``'s exact justification.
Plan 08's search-page extension imports from here rather than duplicating
the fetch-and-assemble loop. ``fetch_prediction_data`` takes only
``ticker`` (no ``asset_class``/``sector`` parameters), since prediction has
no profile-fit/sector logic -- a deliberate single-responsibility deviation
from ``_universe_loader.fetch_scorable_row``'s wider signature.

``fetch_prediction_data`` distinguishes a D-07 "not found" outcome (the
fetch raised, or returned an empty DataFrame) from a D-08 "insufficient
data" outcome (the fetch succeeded but there isn't enough history to
compute reliable, walk-forward-backtestable features) so callers can
render the correct distinct UI state.
"""

import logging

from src.data.prices import fetch_ohlcv
from src.features.feature_frame import assemble_feature_frame
from src.prediction.walk_forward import MIN_PREDICTION_HISTORY_ROWS

logger = logging.getLogger(__name__)


def fetch_prediction_data(ticker: str) -> dict:
    """Fetch and assemble one asset's 5-year prediction data.

    Returns one of:
    - ``{"status": "not_found"}`` -- ``fetch_ohlcv`` raised, or returned an
      empty DataFrame (D-07).
    - ``{"status": "insufficient_data", "chart_df": df}`` -- the fetch
      succeeded with a non-empty ``df``, but the assembled, dropna'd
      feature frame has fewer than ``MIN_PREDICTION_HISTORY_ROWS`` rows
      (D-08). ``chart_df`` is the full, untouched, non-dropna'd fetch
      result.
    - ``{"status": "ok", "chart_df": df, "feature_frame": feature_frame,
      "price_series": price_series}`` -- at least
      ``MIN_PREDICTION_HISTORY_ROWS`` non-NaN feature rows exist.
      ``price_series`` is ``df["Close"]`` aligned to ``feature_frame``'s
      post-dropna index; ``chart_df`` remains the full, untouched fetch
      result.
    """
    try:
        df, _source = fetch_ohlcv(ticker, period="5y")
    except Exception:
        logger.exception("fetch_prediction_data failed for %s", ticker)
        return {"status": "not_found"}

    if df.empty:
        return {"status": "not_found"}

    feature_frame = assemble_feature_frame(df).dropna()
    if len(feature_frame) < MIN_PREDICTION_HISTORY_ROWS:
        return {"status": "insufficient_data", "chart_df": df}

    price_series = df["Close"].loc[feature_frame.index]
    return {
        "status": "ok",
        "chart_df": df,
        "feature_frame": feature_frame,
        "price_series": price_series,
    }
