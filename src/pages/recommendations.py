"""Recommendations page (REC-01/REC-02/REC-03) -- the ranked shortlist.

``render_recommendations_page()`` is a ``require_auth()``-gated,
per-asset-class ranked shortlist. This page is deliberately thin: all
scoring lives in ``src.recommendation.engine`` (Plan 05), all curated-
universe fetching in ``src.pages._universe_loader`` (Plan 01), and all
charts/disclaimer copy in ``src.components`` (Plan 04) -- this module's
only job is orchestration and rendering, mirroring ``src/pages/profile.py``'s
page-thin/module-thick split.

Every composite score, sub-factor breakdown, and explanation sentence
rendered here comes verbatim from the same dict entry
``build_recommendations`` returned for that asset -- this page never
recomputes, re-normalizes, or overrides any of those values, and it never
imports ``yfinance`` or calls ``fetch_ohlcv`` directly (all price/feature
data flows through ``src.pages._universe_loader``).

``require_auth()`` is called first, and only, per D-04 -- no inline auth
logic is duplicated here.
"""

import pandas as pd
import streamlit as st

from src.auth.session import require_auth
from src.components.charts import render_breakdown_bar_chart
from src.components.disclaimer import render_disclaimer_banner
from src.data.profile import fetch_profile
from src.pages._universe_loader import load_universe_rows
from src.recommendation.engine import build_recommendations
from src.recommendation.universe import (
    ASSET_CLASS_SECTORS,
    ASSET_CLASS_TICKERS,
    ASSET_CLASSES,
)

PAGE_HEADING = "Recommendations"
PAGE_SUBHEADING = (
    "Your top-ranked assets across every asset class, scored against your "
    "investor profile."
)
PROFILE_NUDGE_MESSAGE = (
    "Add a few details to your investor profile to personalize these rankings."
)
ENGINE_ERROR_MESSAGE = (
    "We couldn't generate recommendations right now. Please try again shortly."
)
VIEW_DETAILS_LABEL = "View Details"
SCORE_LABEL_TEMPLATE = "{score}/100"
BREAKDOWN_HEADING = "Score Breakdown"

# Any of these being falsy/missing means the profile is incomplete enough to
# warrant the non-blocking personalization nudge (the ranked list still
# renders below regardless, per Phase 2's nullable-fields precedent).
PROFILE_PERSONALIZATION_FIELDS = [
    "risk_tolerance",
    "time_horizon",
    "preferred_sectors",
    "excluded_sectors",
    "preferred_asset_types",
    "capital",
]


def _build_tickers_with_metadata() -> list[tuple[str, str, str | None]]:
    """Build the (ticker, asset_class, sector) triples for every ticker in
    ``universe.ASSET_CLASS_TICKERS`` across all 5 asset classes.

    Only ``"Stocks"`` carries a real sector tag (via
    ``ASSET_CLASS_SECTORS.get(ticker)``); every other asset class passes
    ``None`` for sector, matching ``ASSET_CLASS_SECTORS``'s own
    stocks-only contract.
    """
    tickers_with_metadata: list[tuple[str, str, str | None]] = [
        (ticker, "Stocks", ASSET_CLASS_SECTORS.get(ticker))
        for ticker in ASSET_CLASS_TICKERS["Stocks"]
    ]
    for asset_class in ASSET_CLASSES:
        if asset_class == "Stocks":
            continue
        tickers_with_metadata.extend(
            (ticker, asset_class, None) for ticker in ASSET_CLASS_TICKERS[asset_class]
        )
    return tickers_with_metadata


def render_recommendations_page() -> None:
    """Render the require_auth()-gated, per-asset-class ranked shortlist."""
    user = require_auth()
    access_token = st.session_state["access_token"]

    st.title(PAGE_HEADING)
    st.write(PAGE_SUBHEADING)
    render_disclaimer_banner()

    # Fetched fresh on every render (D-13) -- never cached -- so an edit on
    # the Profile page is reflected on the very next load of this page.
    profile = fetch_profile(access_token, user.id) or {}
    if any(not profile.get(field) for field in PROFILE_PERSONALIZATION_FIELDS):
        st.info(PROFILE_NUDGE_MESSAGE)

    tickers_with_metadata = _build_tickers_with_metadata()
    scorable_rows, _unscorable = load_universe_rows(tickers_with_metadata)

    if not scorable_rows:
        st.error(ENGINE_ERROR_MESSAGE)
        return

    universe_df = pd.DataFrame(scorable_rows)
    grouped = build_recommendations(profile, universe_df)

    for asset_class in ASSET_CLASSES:
        st.subheader(asset_class)
        cards = grouped[asset_class]
        if not cards:
            # D-04/D-05 zero-one-many: the section header still renders,
            # the section itself is simply empty -- never an error.
            continue

        columns = st.columns(len(cards))
        for column, card in zip(columns, cards):
            with column:
                st.subheader(card["ticker"])
                st.write(SCORE_LABEL_TEMPLATE.format(score=card["composite_score_display"]))
                with st.expander(BREAKDOWN_HEADING):
                    render_breakdown_bar_chart(
                        card["sub_scores_display"],
                        key=f"breakdown_{asset_class}_{card['ticker']}",
                    )
                st.write(card["explanation"])
                if st.button(
                    VIEW_DETAILS_LABEL,
                    key=f"view_{asset_class}_{card['ticker']}",
                ):
                    # Deferred import: src.pages.search ships in Plan 07,
                    # which runs immediately after this plan -- importing at
                    # call time (rather than module load time) keeps this
                    # page importable even in the brief window before that
                    # module exists, with zero effect on the navigation
                    # behavior once both pages are registered (Plan 08).
                    from src.pages.search import render_search_page

                    st.switch_page(
                        st.Page(render_search_page, url_path="search"),
                        query_params={"ticker": card["ticker"]},
                    )
