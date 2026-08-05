"""Deterministic within-class factor sub-scores (D-01, D-03).

Every function here takes an already-assembled ``universe_df`` (one row per
asset, with at least an ``"asset_class"`` column plus the raw factor
columns) and returns a ``pandas.Series`` aligned to ``universe_df.index``,
values in the closed range ``[0, 1]``.

Cross-asset-class normalization (D-03) is always computed **within each
asset class's own universe** via ``groupby("asset_class").transform(...)``
-- never globally across the whole universe at once (Pitfall 1). A
within-class group smaller than ``MIN_GROUP_SIZE`` falls back to
``DEFAULT_PERCENTILE_FALLBACK`` instead of producing a degenerate
rank/z-score (Pitfall 2).

This module imports ``pandas`` only -- no ``numpy``, no ``streamlit``, no
``yfinance``, no ``sqlite3``. It never fetches its own data, and it has no
error handling/try-except: guard conditions like "insufficient history"
belong in the orchestration layer that calls this module, not here.
"""

import pandas as pd

MIN_GROUP_SIZE = 3
DEFAULT_PERCENTILE_FALLBACK = 0.5


def _safe_group_percentile(universe_df: pd.DataFrame, column: str) -> pd.Series:
    """Within-class percentile rank of ``column``, with a degenerate-group
    fallback (Pitfall 2).

    Groups with fewer than ``MIN_GROUP_SIZE`` members produce
    ``DEFAULT_PERCENTILE_FALLBACK`` for every row in that group, rather than
    the coarse/degenerate ``rank(pct=True)`` value a tiny group would
    otherwise produce.
    """
    group_sizes = universe_df.groupby("asset_class")[column].transform("size")
    pct = universe_df.groupby("asset_class")[column].transform(lambda s: s.rank(pct=True))
    return pct.where(group_sizes >= MIN_GROUP_SIZE, DEFAULT_PERCENTILE_FALLBACK)


def compute_momentum_score(universe_df: pd.DataFrame) -> pd.Series:
    """Within-class percentile rank of raw ``returns`` -- higher raw
    momentum scores higher within its own asset class."""
    return _safe_group_percentile(universe_df, "returns")


def compute_volatility_score(universe_df: pd.DataFrame) -> pd.Series:
    """Inverted within-class percentile rank of raw ``volatility_20`` --
    lower raw volatility scores higher ("stability"-style reading)."""
    return 1 - _safe_group_percentile(universe_df, "volatility_20")


def compute_quality_score(universe_df: pd.DataFrame) -> pd.Series:
    """Within-class percentile rank of an RSI-neutrality "quality" proxy.

    ``rsi_14`` near the neutral value of 50 reads as highest raw "quality"
    (``1 - abs(rsi_14 - 50) / 50``), per RESEARCH.md Open Question 2's
    resolution to derive quality from existing technicals rather than a new
    fundamentals data source. That raw value is then percentile-ranked
    within class like the other two factors, for consistency.
    """
    working_df = universe_df.copy()
    working_df["_quality_raw"] = 1 - (working_df["rsi_14"] - 50).abs() / 50
    return _safe_group_percentile(working_df, "_quality_raw")
