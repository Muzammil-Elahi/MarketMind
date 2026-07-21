"""Investor profile builder page (PROFILE-01/PROFILE-02).

A single always-editable form (D-12) covers the six scalar profile fields
(risk tolerance, time horizon, preferred/excluded sectors, preferred asset
types, capital) plus a dynamic holdings grid (ticker/quantity/optional cost
basis, D-06/D-07). The same form and the same "Save Profile" button serve
both a first-time user (no profile row exists yet) and a later edit -- there
is no separate view-then-edit-mode toggle and no separate "welcome" copy.

``require_auth()`` is called first, and only, per D-04 -- no inline auth
logic is duplicated here. Every read/write goes through
``src.data.profile``'s CRUD chokepoint (``fetch_profile``/``upsert_profile``/
``fetch_holdings``/``upsert_holdings``/``validate_ticker``) -- this page
never talks to Supabase directly.

Per D-13, the profile and holdings reads below are fetched fresh on every
render -- no function in this file wraps either read in a Streamlit caching
decorator -- so an edit is always reflected on the very next page load with
no explicit cache-invalidation step needed.

This page captures investor preferences only. It must never render any
recommendation, forecast, or personalized investment-advice text, and it
must never import the point-in-time feature-engineering package (that
package's output has no business appearing on this surface -- PROFILE-01's
scope is data capture, not scoring).
"""

import pandas as pd
import streamlit as st

from src.auth.session import require_auth
from src.data.profile import (
    fetch_holdings,
    fetch_profile,
    upsert_holdings,
    upsert_profile,
    validate_ticker,
)

PAGE_HEADING = "Investor Profile"
PAGE_SUBHEADING = (
    "Tell us how you invest so we can tailor your recommendations. "
    "You can update this anytime."
)
HOLDINGS_HEADING = "Existing Holdings"
HOLDINGS_EMPTY_STATE = "No holdings added yet. Add a ticker below to get started."
INVALID_TICKER_ERROR_TEMPLATE = 'We couldn\'t recognize "{ticker}" — check the symbol and try again.'
SAVE_FAILURE_ERROR = "We couldn't save your profile. Please try again."
SAVE_SUCCESS_MESSAGE = "Profile saved."
SAVE_BUTTON_LABEL = "Save Profile"

# UI-SPEC Color contract's "Destructive" token (#DC2626) -- reused here for
# the holdings-grid invalid-ticker highlight, the same red login.py's
# _highlight_empty_fields uses for its own empty-required-field highlight.
FIELD_ERROR_BORDER_COLOR = "#DC2626"

RISK_TOLERANCE_OPTIONS = ["Conservative", "Moderate", "Aggressive"]
TIME_HORIZON_OPTIONS = ["<1yr", "1-3yr", "3-5yr", "5-10yr", "10+yr"]
SECTORS = [
    "Tech",
    "Healthcare",
    "Financials",
    "Energy",
    "Consumer",
    "Industrials",
    "Real Estate",
    "Utilities",
    "Materials",
    "Communication",
]
ASSET_TYPE_OPTIONS = ["Stocks", "ETFs", "Crypto", "Gold", "Forex"]

HOLDINGS_COLUMNS = ["ticker", "quantity", "cost_basis"]


def _highlight_holdings_editor() -> None:
    """Render CSS that puts a red border around the whole holdings editor.

    ``st.data_editor`` exposes no per-cell/per-row CSS key the way
    individual ``st.text_input`` widgets do (contrast with ``login.py``'s
    field-level ``_highlight_empty_fields``) -- so this scopes the border to
    the widget as a whole via its own ``key="holdings_editor"``. Only that
    static, developer-controlled key string is interpolated into
    ``unsafe_allow_html`` -- never a raw ticker string or any other
    user-entered value -- matching ``login.py``'s CSS-injection discipline
    exactly.
    """
    st.markdown(
        "<style>div.st-key-holdings_editor { border: 1px solid "
        + FIELD_ERROR_BORDER_COLOR
        + " !important; border-radius: 0.5rem; }</style>",
        unsafe_allow_html=True,
    )


def render_profile_page() -> None:
    """Render the require_auth()-gated investor profile builder page."""
    user = require_auth()
    access_token = st.session_state["access_token"]
    user_id = user.id

    # Fetched fresh on every render (D-13) so the pre-filled values below
    # always reflect exactly what is currently persisted -- no stale cache.
    existing_profile = fetch_profile(access_token, user_id)
    existing_holdings = fetch_holdings(access_token, user_id)
    profile = existing_profile or {}

    st.title(PAGE_HEADING)
    st.write(PAGE_SUBHEADING)

    with st.form("profile_form"):
        risk_tolerance = profile.get("risk_tolerance")
        risk_tolerance_index = (
            RISK_TOLERANCE_OPTIONS.index(risk_tolerance)
            if risk_tolerance in RISK_TOLERANCE_OPTIONS
            else None
        )
        risk_tolerance_value = st.selectbox(
            "Risk Tolerance", RISK_TOLERANCE_OPTIONS, index=risk_tolerance_index
        )

        time_horizon = profile.get("time_horizon")
        time_horizon_index = (
            TIME_HORIZON_OPTIONS.index(time_horizon)
            if time_horizon in TIME_HORIZON_OPTIONS
            else None
        )
        time_horizon_value = st.selectbox(
            "Time Horizon", TIME_HORIZON_OPTIONS, index=time_horizon_index
        )

        preferred_sectors_value = st.multiselect(
            "Preferred Sectors",
            options=SECTORS,
            default=profile.get("preferred_sectors") or [],
        )
        excluded_sectors_value = st.multiselect(
            "Excluded Sectors",
            options=SECTORS,
            default=profile.get("excluded_sectors") or [],
        )

        st.write("Preferred Asset Types")
        existing_asset_types = profile.get("preferred_asset_types") or []
        asset_type_checkbox_values = {}
        asset_type_columns = st.columns(len(ASSET_TYPE_OPTIONS))
        for column, asset_type in zip(asset_type_columns, ASSET_TYPE_OPTIONS):
            with column:
                asset_type_checkbox_values[asset_type] = st.checkbox(
                    asset_type, value=asset_type in existing_asset_types
                )

        capital_value = st.number_input(
            "Capital", min_value=0.0, value=float(profile.get("capital") or 0.0)
        )

        st.subheader(HOLDINGS_HEADING)
        if not existing_holdings:
            st.caption(HOLDINGS_EMPTY_STATE)
        holdings_df = pd.DataFrame(
            [
                {
                    "ticker": row["ticker"],
                    "quantity": row["quantity"],
                    "cost_basis": row.get("cost_basis"),
                }
                for row in existing_holdings
            ],
            columns=HOLDINGS_COLUMNS,
        )
        edited_holdings = st.data_editor(
            holdings_df,
            num_rows="dynamic",
            key="holdings_editor",
            column_config={
                "ticker": st.column_config.TextColumn("Ticker"),
                "quantity": st.column_config.NumberColumn("Quantity"),
                "cost_basis": st.column_config.NumberColumn("Cost Basis"),
            },
        )

        submitted = st.form_submit_button(SAVE_BUTTON_LABEL)

    if not submitted:
        return

    # Skip any row with a blank ticker (an unfilled newly-added row) before
    # validating -- an empty row is not a submission attempt, not an error.
    holdings_rows = []
    for _, row in edited_holdings.iterrows():
        ticker_value = row.get("ticker")
        if pd.isna(ticker_value):
            continue
        ticker = str(ticker_value).strip()
        if not ticker:
            continue
        quantity_value = row.get("quantity")
        quantity_value = None if pd.isna(quantity_value) else quantity_value
        cost_basis_value = row.get("cost_basis")
        cost_basis_value = None if pd.isna(cost_basis_value) else cost_basis_value
        holdings_rows.append(
            {"ticker": ticker, "quantity": quantity_value, "cost_basis": cost_basis_value}
        )

    invalid_tickers = [row["ticker"] for row in holdings_rows if not validate_ticker(row["ticker"])]

    if invalid_tickers:
        for ticker in invalid_tickers:
            st.error(INVALID_TICKER_ERROR_TEMPLATE.format(ticker=ticker))
        _highlight_holdings_editor()
        return

    preferred_asset_types_value = [
        asset_type for asset_type, checked in asset_type_checkbox_values.items() if checked
    ]

    try:
        upsert_profile(
            access_token,
            user_id,
            risk_tolerance=risk_tolerance_value,
            time_horizon=time_horizon_value,
            preferred_sectors=preferred_sectors_value,
            excluded_sectors=excluded_sectors_value,
            preferred_asset_types=preferred_asset_types_value,
            capital=capital_value,
        )
        upsert_holdings(access_token, user_id, holdings_rows)
    except Exception:
        st.error(SAVE_FAILURE_ERROR)
        return

    st.success(SAVE_SUCCESS_MESSAGE)
    st.rerun()
