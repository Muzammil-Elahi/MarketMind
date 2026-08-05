"""Tests for src/pages/search.py's resolve_search_result (REC-04, D-07/D-08).

Fully mocked -- no live network call. Patches the names as imported into
src.pages.search (mirrors tests/test_ticker_validation.py's convention),
never the real src.pages._universe_loader.fetch_scorable_row/
load_universe_rows implementations.
"""

from unittest.mock import patch

import pandas as pd

from src.pages.search import resolve_search_result
from src.recommendation.engine import build_recommendations


def _minimal_profile(**overrides):
    profile = {
        "risk_tolerance": "Moderate",
        "excluded_sectors": [],
        "preferred_asset_types": [],
        "preferred_sectors": [],
        "time_horizon": None,
    }
    profile.update(overrides)
    return profile


def _sample_chart_df():
    return pd.DataFrame({"Close": [100.0, 101.0, 102.0]})


def _aapl_feature_row():
    return {
        "ticker": "AAPL",
        "asset_class": "Stocks",
        "sector": "Tech",
        "returns": 0.01,
        "volatility_20": 0.02,
        "rsi_14": 55.0,
    }


def _synthetic_stocks_peer_rows():
    """3 synthetic Stocks peers, internally varied on every raw factor --
    mirrors tests/test_recommendation_engine.py's synthetic-data style."""
    return [
        {
            "ticker": "PEER_A",
            "asset_class": "Stocks",
            "sector": "Healthcare",
            "returns": 0.03,
            "volatility_20": 0.15,
            "rsi_14": 50.0,
        },
        {
            "ticker": "PEER_B",
            "asset_class": "Stocks",
            "sector": "Energy",
            "returns": -0.01,
            "volatility_20": 0.25,
            "rsi_14": 45.0,
        },
        {
            "ticker": "PEER_C",
            "asset_class": "Stocks",
            "sector": "Financials",
            "returns": 0.02,
            "volatility_20": 0.20,
            "rsi_14": 60.0,
        },
    ]


# --- empty_query -----------------------------------------------------------


def test_resolve_search_result_empty_string_returns_empty_query():
    profile = _minimal_profile()

    result = resolve_search_result("", profile)

    assert result == {"status": "empty_query"}


def test_resolve_search_result_whitespace_only_returns_empty_query():
    profile = _minimal_profile()

    result = resolve_search_result("   ", profile)

    assert result == {"status": "empty_query"}


def test_fetch_ohlcv_never_called_for_blank_query():
    """REC-04 empty: no fetch is attempted at all for a blank query --
    proven by a mock-call-count assertion on the underlying fetch_ohlcv
    chokepoint, not just a return-value check."""
    profile = _minimal_profile()

    with patch("src.pages._universe_loader.fetch_ohlcv") as mock_fetch_ohlcv:
        result = resolve_search_result("", profile)

    assert result == {"status": "empty_query"}
    mock_fetch_ohlcv.assert_not_called()


# --- not_found (D-07) -------------------------------------------------------


def test_resolve_search_result_not_found():
    profile = _minimal_profile()

    with patch(
        "src.pages.search.fetch_scorable_row", return_value={"status": "not_found"}
    ):
        result = resolve_search_result("NOTAREAL", profile)

    assert result == {"status": "not_found", "ticker": "NOTAREAL"}


# --- insufficient_data (D-08) -----------------------------------------------


def test_resolve_search_result_insufficient_data():
    profile = _minimal_profile()
    chart_df = _sample_chart_df()

    with patch(
        "src.pages.search.fetch_scorable_row",
        return_value={"status": "insufficient_data", "chart_df": chart_df},
    ):
        result = resolve_search_result("NEWIPO", profile)

    assert result["status"] == "insufficient_data"
    assert result["ticker"] == "NEWIPO"
    assert result["chart_df"] is chart_df


# --- scored ------------------------------------------------------------------


def test_resolve_search_result_scored():
    profile = _minimal_profile()
    chart_df = _sample_chart_df()
    peer_rows = _synthetic_stocks_peer_rows()

    with (
        patch(
            "src.pages.search.fetch_scorable_row",
            return_value={
                "status": "ok",
                "chart_df": chart_df,
                "feature_row": _aapl_feature_row(),
            },
        ),
        patch(
            "src.pages.search.load_universe_rows",
            return_value=(peer_rows, []),
        ),
    ):
        result = resolve_search_result("AAPL", profile)

    assert result["status"] == "scored"
    assert result["ticker"] == "AAPL"
    assert result["chart_df"] is chart_df
    assert "composite_score" in result
    assert "composite_score_display" in result
    assert "sub_scores" in result
    assert "sub_scores_display" in result
    assert "explanation" in result


def test_resolve_search_result_single_source_of_truth_matches_build_recommendations():
    """REC-04 adjacency: resolve_search_result's composite_score for AAPL is
    numerically identical to build_recommendations's composite_score for
    the same ticker against the same synthetic peer data -- both paths call
    score_universe with the identical combined DataFrame content."""
    profile = _minimal_profile()
    chart_df = _sample_chart_df()
    peer_rows = _synthetic_stocks_peer_rows()
    aapl_feature_row = _aapl_feature_row()

    with (
        patch(
            "src.pages.search.fetch_scorable_row",
            return_value={
                "status": "ok",
                "chart_df": chart_df,
                "feature_row": aapl_feature_row,
            },
        ),
        patch(
            "src.pages.search.load_universe_rows",
            return_value=(peer_rows, []),
        ),
    ):
        search_result = resolve_search_result("AAPL", profile)

    combined_df = pd.DataFrame(peer_rows + [aapl_feature_row])
    recommendations = build_recommendations(profile, combined_df)
    aapl_row = next(row for row in recommendations["Stocks"] if row["ticker"] == "AAPL")

    assert search_result["composite_score"] == aapl_row["composite_score"]


def test_resolve_search_result_bypasses_hard_exclude():
    """Search deliberately does NOT apply profile_fit's hard-exclude
    filter -- a searched asset outside the user's excluded_sectors still
    returns a real score (D-07's search escape hatch)."""
    profile = _minimal_profile(excluded_sectors=["Tech"])
    chart_df = _sample_chart_df()
    peer_rows = _synthetic_stocks_peer_rows()

    with (
        patch(
            "src.pages.search.fetch_scorable_row",
            return_value={
                "status": "ok",
                "chart_df": chart_df,
                "feature_row": _aapl_feature_row(),
            },
        ),
        patch(
            "src.pages.search.load_universe_rows",
            return_value=(peer_rows, []),
        ),
    ):
        result = resolve_search_result("AAPL", profile)

    assert result["status"] == "scored"
    assert isinstance(result["composite_score"], float)
