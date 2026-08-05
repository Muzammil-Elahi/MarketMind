"""Tests for src/recommendation/profile_fit.py (REC-02, D-01's profile-fit sub-score).

Pure, zero-I/O plain-dict fixtures -- no network calls, no yfinance, no
Streamlit, no pandas DataFrame. Mirrors tests/test_features_technical.py's
synthetic-data style.
"""

from src.recommendation.profile_fit import compute_profile_fit, is_excluded


def test_is_excluded_true_when_sector_in_excluded_sectors():
    asset_row = {"sector": "Energy", "asset_class": "Stocks"}
    profile = {"excluded_sectors": ["Energy"]}

    assert is_excluded(asset_row, profile) is True


def test_is_excluded_true_when_asset_class_not_in_preferred_asset_types():
    asset_row = {"sector": "Tech", "asset_class": "Crypto"}
    profile = {"preferred_asset_types": ["Stocks"]}

    assert is_excluded(asset_row, profile) is True


def test_is_excluded_false_when_preferred_asset_types_empty():
    asset_row = {"sector": "Tech", "asset_class": "Stocks"}
    profile = {"preferred_asset_types": []}

    assert is_excluded(asset_row, profile) is False


def test_is_excluded_false_when_sector_none_never_matches_exclusion():
    asset_row = {"sector": None, "asset_class": "Crypto"}
    profile = {"excluded_sectors": ["Energy"], "preferred_asset_types": []}

    assert is_excluded(asset_row, profile) is False


def test_compute_profile_fit_responds_to_preferred_sector_and_time_horizon():
    preferred_asset = {
        "sector": "Tech",
        "asset_class": "Stocks",
        "momentum_pct": 0.6,
    }
    non_preferred_asset = {
        "sector": "Healthcare",
        "asset_class": "Stocks",
        "momentum_pct": 0.6,
    }
    profile_long_horizon = {"preferred_sectors": ["Tech"], "time_horizon": "10+yr"}
    profile_short_horizon = {"preferred_sectors": ["Tech"], "time_horizon": "<1yr"}

    high_score = compute_profile_fit(preferred_asset, profile_long_horizon)
    low_score = compute_profile_fit(non_preferred_asset, profile_short_horizon)

    assert high_score > low_score


def test_compute_profile_fit_always_bounded_zero_to_one_with_missing_fields():
    asset_row = {"sector": None, "asset_class": "Gold"}
    profile = {}

    score = compute_profile_fit(asset_row, profile)

    assert 0.0 <= score <= 1.0
