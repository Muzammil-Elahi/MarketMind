"""The single shared feature-assembly entry point.

``assemble_feature_frame`` is the one function this phase's tests and a
future backtest harness / live inference call — no duplicated
feature-computation logic exists elsewhere (ROADMAP Phase 2 success
criterion #4). It calls only ``src.features.technical`` functions; it never
reimplements any rolling-window logic inline.
"""

import pandas as pd

from src.features import technical


def assemble_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Assemble the point-in-time feature frame for a single asset.

    Parameters
    ----------
    df:
        An already-fetched OHLCV DataFrame (capitalized columns, e.g. from
        ``src.data.prices.fetch_ohlcv``), time-sorted ascending.

    Returns
    -------
    A DataFrame indexed identically to ``df.index`` with exactly the
    columns ``"returns"``, ``"volatility_20"``, ``"sma_20"``, ``"rsi_14"``.
    """
    features = pd.DataFrame(index=df.index)
    features["returns"] = technical.compute_returns(df)
    features["volatility_20"] = technical.compute_volatility(df, window=20)
    features["sma_20"] = technical.compute_sma(df, window=20)
    features["rsi_14"] = technical.compute_rsi(df, window=14)
    return features
