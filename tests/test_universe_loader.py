"""Tests for src/pages/_universe_loader.py (REC-01/REC-04, D-07/D-08).

Mirrors tests/test_ticker_validation.py's unittest.mock.patch style: mock
src.pages._universe_loader.fetch_ohlcv directly (the name as imported into
this module) rather than exercising the real yfinance chokepoint. No live
network call occurs anywhere in this file.
"""

from unittest.mock import patch

import numpy as np
import pandas as pd

from src.pages._universe_loader import (
    fetch_scorable_row,
    load_asset_feature_row,
    load_universe_rows,
)
from src.recommendation.universe import MIN_HISTORY_ROWS


def _sample_ohlcv(n_rows: int) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n_rows, freq="D")
    close = pd.Series(
        100 + np.sin(np.arange(n_rows) / 3.0) * 5 + np.arange(n_rows) * 0.5,
        index=dates,
        dtype=float,
    )
    return pd.DataFrame(
        {"Open": close, "High": close + 1, "Low": close - 1, "Close": close}
    )


def test_fetch_scorable_row_not_found_on_exception():
    with patch(
        "src.pages._universe_loader.fetch_ohlcv",
        side_effect=RuntimeError("simulated failure"),
    ):
        result = fetch_scorable_row("NOTATICKER", "Stocks", "Tech")

    assert result == {"status": "not_found"}


def test_fetch_scorable_row_not_found_on_empty_dataframe():
    with patch(
        "src.pages._universe_loader.fetch_ohlcv",
        return_value=(pd.DataFrame(), "live"),
    ):
        result = fetch_scorable_row("NOTATICKER", "Stocks", "Tech")

    assert result == {"status": "not_found"}


def test_fetch_scorable_row_insufficient_data_for_thin_history():
    thin_df = _sample_ohlcv(n_rows=10)
    assert MIN_HISTORY_ROWS > 10
    with patch(
        "src.pages._universe_loader.fetch_ohlcv",
        return_value=(thin_df, "live"),
    ):
        result = fetch_scorable_row("NEWIPO", "Stocks", "Tech")

    assert result["status"] == "insufficient_data"
    pd.testing.assert_frame_equal(result["chart_df"], thin_df)


def test_fetch_scorable_row_ok_for_sufficient_history():
    full_df = _sample_ohlcv(n_rows=60)
    with patch(
        "src.pages._universe_loader.fetch_ohlcv",
        return_value=(full_df, "live"),
    ):
        result = fetch_scorable_row("AAPL", "Stocks", "Tech")

    assert result["status"] == "ok"
    pd.testing.assert_frame_equal(result["chart_df"], full_df)
    feature_row = result["feature_row"]
    assert feature_row["ticker"] == "AAPL"
    assert feature_row["asset_class"] == "Stocks"
    assert feature_row["sector"] == "Tech"
    assert not pd.isna(feature_row["returns"])
    assert not pd.isna(feature_row["volatility_20"])
    assert not pd.isna(feature_row["rsi_14"])


def test_load_asset_feature_row_returns_none_when_not_scorable():
    with patch(
        "src.pages._universe_loader.fetch_ohlcv",
        return_value=(pd.DataFrame(), "live"),
    ):
        result = load_asset_feature_row("NOTATICKER", "Stocks", "Tech")

    assert result is None


def test_load_asset_feature_row_returns_feature_row_dict_when_scorable():
    full_df = _sample_ohlcv(n_rows=60)
    with patch(
        "src.pages._universe_loader.fetch_ohlcv",
        return_value=(full_df, "live"),
    ):
        result = load_asset_feature_row("AAPL", "Stocks", "Tech")

    assert result is not None
    assert result["ticker"] == "AAPL"


def test_load_universe_rows_splits_scorable_and_unscorable():
    full_df = _sample_ohlcv(n_rows=60)
    thin_df = _sample_ohlcv(n_rows=10)

    def _fake_fetch_ohlcv(ticker, **kwargs):
        if ticker == "AAPL":
            return full_df, "live"
        if ticker == "NEWIPO":
            return thin_df, "live"
        raise RuntimeError("simulated failure")

    with patch(
        "src.pages._universe_loader.fetch_ohlcv", side_effect=_fake_fetch_ohlcv
    ):
        scorable_rows, unscorable_tickers = load_universe_rows(
            [
                ("AAPL", "Stocks", "Tech"),
                ("NEWIPO", "Stocks", "Tech"),
                ("NOTATICKER", "Stocks", "Tech"),
            ]
        )

    assert len(scorable_rows) == 1
    assert scorable_rows[0]["ticker"] == "AAPL"
    assert unscorable_tickers == ["NEWIPO", "NOTATICKER"]
