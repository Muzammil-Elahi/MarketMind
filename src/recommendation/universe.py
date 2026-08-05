"""Curated, fixed cross-asset-class universe (D-04).

Every ticker list below is a static Python literal -- never live-pulled from
an index/market-cap source. Sector tags for ``STOCK_UNIVERSE`` are hardcoded
static metadata (Pitfall 3): this module never calls ``yf.Ticker(...).info``
or any other live sector/fundamentals lookup. This file has zero I/O and
imports nothing beyond the standard library.

Ticker convention (yfinance): ``=X`` suffix for forex pairs (e.g.
``EURUSD=X``), a dash-separated ``-USD`` quote for crypto (e.g.
``BTC-USD``), and ``=F`` for futures (e.g. ``GC=F`` for gold futures).
"""

from __future__ import annotations

# (ticker, sector) -- sector values match src/pages/profile.py's SECTORS
# list exactly, so recommendation/profile_fit.py's sector include/exclude
# logic can match directly with no normalization step.
STOCK_UNIVERSE: list[tuple[str, str]] = [
    ("AAPL", "Tech"), ("MSFT", "Tech"), ("NVDA", "Tech"),
    ("JNJ", "Healthcare"), ("UNH", "Healthcare"), ("PFE", "Healthcare"),
    ("JPM", "Financials"), ("V", "Financials"), ("BAC", "Financials"),
    ("XOM", "Energy"), ("CVX", "Energy"),
    ("AMZN", "Consumer"), ("PG", "Consumer"), ("KO", "Consumer"),
    ("HON", "Industrials"), ("CAT", "Industrials"),
    ("PLD", "Real Estate"), ("AMT", "Real Estate"),
    ("NEE", "Utilities"), ("DUK", "Utilities"),
    ("LIN", "Materials"), ("FCX", "Materials"),
    ("META", "Communication"), ("GOOGL", "Communication"),
]

ETF_UNIVERSE: list[str] = [
    "SPY", "QQQ", "VTI", "VOO", "DIA", "IWM",
    "XLK", "XLF", "XLE", "XLV", "XLY", "XLI",
]

CRYPTO_UNIVERSE: list[str] = [
    "BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "SOL-USD", "ADA-USD",
    "DOGE-USD", "TRX-USD", "AVAX-USD", "LINK-USD", "DOT-USD", "LTC-USD",
]

GOLD_UNIVERSE: list[str] = ["GC=F", "GLD"]

FOREX_UNIVERSE: list[str] = [
    "EURUSD=X", "USDJPY=X", "GBPUSD=X", "USDCHF=X",
    "AUDUSD=X", "USDCAD=X", "NZDUSD=X", "EURGBP=X",
]

# Order matches src/pages/profile.py's ASSET_TYPE_OPTIONS exactly.
ASSET_CLASSES: list[str] = ["Stocks", "ETFs", "Crypto", "Gold", "Forex"]

ASSET_CLASS_TICKERS: dict[str, list[str]] = {
    "Stocks": [ticker for ticker, _sector in STOCK_UNIVERSE],
    "ETFs": ETF_UNIVERSE,
    "Crypto": CRYPTO_UNIVERSE,
    "Gold": GOLD_UNIVERSE,
    "Forex": FOREX_UNIVERSE,
}

# ticker -> sector; only meaningful for Stocks. ``.get(ticker)`` returns
# ``None`` for every other asset class, which is the intended behavior.
ASSET_CLASS_SECTORS: dict[str, str] = dict(STOCK_UNIVERSE)

# A4: the longest lookback window among returns/volatility_20/sma_20/rsi_14
# is 20 (volatility_20/sma_20) -- the binding minimum-history constraint
# (RESEARCH.md Pattern 6).
MIN_HISTORY_ROWS: int = 20


def infer_asset_class(ticker: str) -> str:
    """Deterministically classify a free-text ticker into one of the 5
    supported asset classes, using yfinance's own suffix convention.

    Checks, in order: ``=X`` suffix -> Forex; ``-USD`` suffix -> Crypto;
    a known gold ticker or ``=F`` suffix -> Gold; else falls back to
    Stocks (Stocks/ETFs share no distinguishing ticker suffix, so Stocks is
    used as the broader default).
    """
    if ticker.endswith("=X"):
        return "Forex"
    if ticker.endswith("-USD"):
        return "Crypto"
    if ticker in GOLD_UNIVERSE or ticker.endswith("=F"):
        return "Gold"
    return "Stocks"
