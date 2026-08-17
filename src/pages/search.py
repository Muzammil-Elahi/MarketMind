"""Search page (REC-04) -- free-text ticker lookup and drill-in.

``resolve_search_result(ticker, profile)`` is the testable core: it reuses
the exact same ``src.recommendation.engine.score_universe`` scoring path
the ranked-list page (``src.pages.recommendations``) uses, so a searched
asset's composite score is never computed by a second, independently
implemented formula (REC-04 single-source-of-truth). It calls
``score_universe(..., apply_hard_exclude=False)`` -- search is the
explicit escape hatch that lets a user view any asset's score regardless
of their profile's preferred/excluded sector or asset-type restrictions.

``render_search_page()`` is the thin ``require_auth()``-gated Streamlit
wrapper around it, mirroring ``src/pages/recommendations.py``'s
page-thin/module-thick split -- all scoring math lives in
``src.recommendation.engine``, all price/feature I/O in
``src.pages._universe_loader``, and all charts/disclaimer copy in
``src.components``. This page never imports ``yfinance`` or calls
``fetch_ohlcv`` directly.
"""

import pandas as pd
import streamlit as st

from src.auth.session import require_auth
from src.components.charts import (
    render_breakdown_bar_chart,
    render_forecast_chart,
    render_price_history_chart,
)
from src.components.disclaimer import render_disclaimer_banner
from src.config import CACHE_TTL_SECONDS
from src.data.profile import fetch_profile
from src.pages._prediction_loader import fetch_prediction_data
from src.pages._universe_loader import fetch_scorable_row, load_universe_rows
from src.prediction.engine import MODEL_LABELS, VALID_HORIZONS, generate_forecast
from src.prediction.metrics import format_metrics_for_display
from src.recommendation.engine import score_universe
from src.recommendation.universe import ASSET_CLASS_SECTORS, ASSET_CLASS_TICKERS, infer_asset_class

PAGE_HEADING = "Search"
PAGE_SUBHEADING = (
    "Look up any asset — stock, ETF, crypto, gold, or forex pair — even if "
    "it's not in your recommendations."
)
SEARCH_INPUT_LABEL = "Ticker Symbol"
SEARCH_INPUT_PLACEHOLDER = "e.g. AAPL, BTC-USD, GC=F, EURUSD=X"
SEARCH_BUTTON_LABEL = "Search"
EMPTY_STATE_MESSAGE = "Search for any asset to see its score, breakdown, and price history."
NOT_FOUND_TEMPLATE = 'We couldn\'t find "{ticker}" — check the symbol and try again.'
INSUFFICIENT_DATA_BADGE = "Insufficient data for scoring"
INSUFFICIENT_DATA_BODY_TEMPLATE = (
    "We don't have enough price history for {ticker} yet to compute a "
    "score — here's what we have."
)
SCORE_LABEL_TEMPLATE = "{score}/100"
BREAKDOWN_HEADING = "Score Breakdown"

MODEL_DROPDOWN_LABEL = "Prediction Model"
MODEL_DROPDOWN_PLACEHOLDER = "Select a model"
HORIZON_SELECTOR_LABEL = "Forecast Horizon"
GENERATE_FORECAST_LABEL = "Generate Forecast"
PRE_GENERATION_HINT = (
    "Select a model and horizon, then click Generate Forecast to see a prediction."
)
CI_CAPTION = "Shaded band shows an 80% confidence interval."
BACKTEST_SECTION_HEADING = "Backtested Accuracy"
BACKTEST_HYPOTHETICAL_CAPTION = (
    "Backtested using walk-forward validation on historical data. Hypothetical "
    "results — past performance does not guarantee future accuracy."
)
METRIC_LABELS = {
    "rmse": "RMSE",
    "directional_accuracy": "Directional Accuracy",
    "sharpe": "Sharpe Ratio (Simulated)",
}
INSUFFICIENT_HISTORY_MESSAGE = (
    "Not enough price history to generate a reliable forecast for this asset."
)
PROPHET_UNAVAILABLE_MESSAGE = (
    "Prophet isn't available right now — try SMA Baseline or XGBoost instead."
)
FORECAST_ERROR_MESSAGE = (
    "We couldn't generate a forecast right now. Please try again shortly."
)
HORIZON_LABELS = {7: "7 Days", 30: "30 Days", 90: "90 Days"}


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def resolve_forecast_request(
    ticker: str,
    model: str,
    horizon_days: int,
    feature_frame: pd.DataFrame,
    price_series: pd.Series,
    asset_class: str,
) -> dict:
    """Cached thin wrapper around ``generate_forecast`` (T-04-03 DoS
    mitigation).

    ``src.prediction.engine`` stays zero-I/O and cannot import
    ``streamlit`` itself, so the ``st.cache_data`` memoization boundary
    must live here, at the page layer. Keyed on all six arguments
    including the ``feature_frame``/``price_series`` DataFrame/Series
    content (Streamlit's built-in DataFrame/Series hashing handles this) --
    a repeat "Generate Forecast" click with identical arguments is served
    from cache instantly instead of re-running a CPU-heavy model training
    pass.
    """
    return generate_forecast(ticker, model, horizon_days, feature_frame, price_series, asset_class)


def resolve_search_result(ticker: str, profile: dict) -> dict:
    """Resolve a free-text ticker search into a testable result dict.

    Returns one of:
    - ``{"status": "empty_query"}`` -- blank/whitespace-only input; no
      fetch is attempted (REC-04 empty).
    - ``{"status": "not_found", "ticker": ticker}`` -- ``fetch_scorable_row``
      couldn't resolve the ticker at all (D-07).
    - ``{"status": "insufficient_data", "ticker": ticker, "chart_df": df}``
      -- the ticker resolved but has too little history to score (D-08).
    - ``{"status": "scored", "ticker": ticker, "chart_df": df,
      "composite_score": ..., "composite_score_display": ...,
      "sub_scores": {...}, "sub_scores_display": {...},
      "explanation": ...}`` -- scored via the identical
      ``score_universe`` pipeline the ranked list uses, against the
      searched asset's curated-universe peers, with
      ``apply_hard_exclude=False`` (REC-04's search escape hatch).
    """
    ticker = (ticker or "").strip()
    if not ticker:
        return {"status": "empty_query"}

    asset_class = infer_asset_class(ticker)
    sector = ASSET_CLASS_SECTORS.get(ticker)
    result = fetch_scorable_row(ticker, asset_class, sector)

    if result["status"] == "not_found":
        return {"status": "not_found", "ticker": ticker}

    if result["status"] == "insufficient_data":
        return {"status": "insufficient_data", "ticker": ticker, "chart_df": result["chart_df"]}

    peer_tickers = [t for t in ASSET_CLASS_TICKERS[asset_class] if t != ticker]
    peer_metadata = [(t, asset_class, ASSET_CLASS_SECTORS.get(t)) for t in peer_tickers]
    peer_rows, _unscorable = load_universe_rows(peer_metadata)
    combined_df = pd.DataFrame(peer_rows + [result["feature_row"]])
    scored_df = score_universe(profile, combined_df, apply_hard_exclude=False)

    matching = scored_df[scored_df["ticker"] == ticker]
    if matching.empty:
        # Defensive fallback -- should not normally occur.
        return {"status": "not_found", "ticker": ticker}

    return {
        "status": "scored",
        "ticker": ticker,
        "chart_df": result["chart_df"],
        **matching.iloc[0].to_dict(),
    }


def render_search_page() -> None:
    """Render the require_auth()-gated free-text ticker search page."""
    user = require_auth()
    access_token = st.session_state["access_token"]
    profile = fetch_profile(access_token, user.id) or {}

    st.title(PAGE_HEADING)
    st.write(PAGE_SUBHEADING)
    render_disclaimer_banner()

    # Pre-filled when arriving via a Recommendations-page "View Details"
    # click (Plan 06).
    query_ticker = st.query_params.get("ticker", "")

    with st.form("search_form"):
        ticker_input = st.text_input(
            SEARCH_INPUT_LABEL, value=query_ticker, placeholder=SEARCH_INPUT_PLACEHOLDER
        )
        submitted = st.form_submit_button(SEARCH_BUTTON_LABEL)

    active_ticker = ticker_input if (submitted or query_ticker) else ""
    if not active_ticker.strip():
        st.caption(EMPTY_STATE_MESSAGE)
        return

    result = resolve_search_result(active_ticker, profile)

    if result["status"] == "not_found":
        st.error(NOT_FOUND_TEMPLATE.format(ticker=result["ticker"]))
        return

    if result["status"] == "insufficient_data":
        st.warning(INSUFFICIENT_DATA_BADGE)
        st.write(INSUFFICIENT_DATA_BODY_TEMPLATE.format(ticker=result["ticker"]))
        render_price_history_chart(result["chart_df"], key=f"chart_{result['ticker']}")
        return

    st.subheader(result["ticker"])
    st.write(SCORE_LABEL_TEMPLATE.format(score=result["composite_score_display"]))
    render_price_history_chart(result["chart_df"], key=f"chart_{result['ticker']}")
    st.subheader(BREAKDOWN_HEADING)
    render_breakdown_bar_chart(result["sub_scores_display"], key=f"breakdown_{result['ticker']}")
    st.write(result["explanation"])
