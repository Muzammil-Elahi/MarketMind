"""Public price-data entry point for the rest of the codebase.

Later phases' recommendation/prediction code must import ``fetch_ohlcv``
from here, not from ``src.data.cache`` directly, and this module never
imports ``yfinance`` -- ``src/data/cache.py`` remains the single chokepoint
permitted to do so (RESEARCH.md Pattern 3 / Shared Patterns).
"""

from src.data.cache import fetch_ohlcv

__all__ = ["fetch_ohlcv"]
