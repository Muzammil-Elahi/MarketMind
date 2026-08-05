"""Tests for src/recommendation/universe.py (REC-01/REC-04).

No network calls, no yfinance, no Streamlit -- universe.py is a pure,
zero-I/O static-data module: these tests exercise that contract directly.
"""

import inspect

from src.pages.profile import ASSET_TYPE_OPTIONS, SECTORS
from src.recommendation import universe
from src.recommendation.universe import (
    ASSET_CLASS_SECTORS,
    ASSET_CLASS_TICKERS,
    ASSET_CLASSES,
    CRYPTO_UNIVERSE,
    ETF_UNIVERSE,
    FOREX_UNIVERSE,
    GOLD_UNIVERSE,
    MIN_HISTORY_ROWS,
    STOCK_UNIVERSE,
    infer_asset_class,
)


def test_infer_asset_class_forex():
    assert infer_asset_class("EURUSD=X") == "Forex"


def test_infer_asset_class_crypto():
    assert infer_asset_class("BTC-USD") == "Crypto"


def test_infer_asset_class_gold_future_and_etf():
    assert infer_asset_class("GC=F") == "Gold"
    assert infer_asset_class("GLD") == "Gold"


def test_infer_asset_class_default_stocks():
    assert infer_asset_class("AAPL") == "Stocks"


def test_asset_classes_matches_profile_asset_type_options_exactly():
    assert ASSET_CLASSES == ASSET_TYPE_OPTIONS
    assert ASSET_CLASSES == ["Stocks", "ETFs", "Crypto", "Gold", "Forex"]


def test_no_ticker_appears_in_more_than_one_universe_list():
    stock_tickers = [ticker for ticker, _sector in STOCK_UNIVERSE]
    all_tickers = stock_tickers + ETF_UNIVERSE + CRYPTO_UNIVERSE + GOLD_UNIVERSE + FOREX_UNIVERSE
    assert len(all_tickers) == len(set(all_tickers))


def test_every_stock_sector_is_a_member_of_profile_sectors():
    for _ticker, sector in STOCK_UNIVERSE:
        assert sector in SECTORS


def test_asset_class_tickers_matches_universe_lists():
    assert ASSET_CLASS_TICKERS["Stocks"] == [ticker for ticker, _sector in STOCK_UNIVERSE]
    assert ASSET_CLASS_TICKERS["ETFs"] == ETF_UNIVERSE
    assert ASSET_CLASS_TICKERS["Crypto"] == CRYPTO_UNIVERSE
    assert ASSET_CLASS_TICKERS["Gold"] == GOLD_UNIVERSE
    assert ASSET_CLASS_TICKERS["Forex"] == FOREX_UNIVERSE


def test_asset_class_sectors_only_meaningful_for_stocks():
    ticker, sector = STOCK_UNIVERSE[0]
    assert ASSET_CLASS_SECTORS[ticker] == sector
    assert ASSET_CLASS_SECTORS.get("BTC-USD") is None
    assert ASSET_CLASS_SECTORS.get("SPY") is None


def test_min_history_rows_is_twenty():
    assert MIN_HISTORY_ROWS == 20


def test_universe_module_has_zero_io_imports():
    source = inspect.getsource(universe)
    assert "import streamlit" not in source
    assert "import yfinance" not in source
    assert "import sqlite3" not in source
