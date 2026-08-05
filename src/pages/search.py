"""Search page (REC-04) -- free-text ticker lookup and drill-in.

``resolve_search_result(ticker, profile)`` is the testable core: it reuses
the exact same ``src.recommendation.engine.score_universe`` scoring path
the ranked-list page (``src.pages.recommendations``) uses, so a searched
asset's composite score is never computed by a second, independently
implemented formula (REC-04 single-source-of-truth). It calls
``score_universe(..., apply_hard_exclude=False)`` -- search is the
explicit escape hatch that lets a user view any asset's score regardless
of their profile's preferred/excluded sector or asset-type restrictions.

``render_search_page()`` (added in the following task) is the thin
``require_auth()``-gated Streamlit wrapper around it.
"""

import pandas as pd

from src.pages._universe_loader import fetch_scorable_row, load_universe_rows
from src.recommendation.engine import score_universe
from src.recommendation.universe import ASSET_CLASS_SECTORS, ASSET_CLASS_TICKERS, infer_asset_class


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
