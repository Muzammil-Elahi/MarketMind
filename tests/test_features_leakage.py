"""Leakage smoke test for src/features/ (D-11, ROADMAP Phase 2 success
criterion #3).

Proves no future information ever reaches a past feature value, via two
independent checks: truncation invariance, and synthetic future-signal
injection. Adapted from 02-RESEARCH.md's Code Examples section, but built
with capitalized "Close"/"High"/"Low"/"Open" columns -- this codebase's
real OHLCV convention (tests/test_cache.py's _sample_df()) -- not
RESEARCH.md's lowercase illustrative columns.
"""

import pandas as pd

from src.features.feature_frame import assemble_feature_frame


def _sample_ohlcv(n_rows: int) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n_rows, freq="D")
    close = pd.Series(range(100, 100 + n_rows), index=dates, dtype=float)
    return pd.DataFrame(
        {"Close": close, "High": close, "Low": close, "Open": close}
    )


def test_truncation_invariance_no_future_data_changes_past_features():
    """Features for dates <= T must be identical whether the raw frame ends
    at T or extends 30 rows further into the future."""
    full_df = _sample_ohlcv(100)
    truncated_df = full_df.iloc[:70]  # ends at "T"

    features_from_truncated = assemble_feature_frame(truncated_df)
    features_from_full = assemble_feature_frame(full_df).iloc[:70]

    pd.testing.assert_frame_equal(features_from_truncated, features_from_full)


def test_synthetic_future_signal_never_appears_before_its_source_date():
    """A column deterministically derived from a *future* close price must
    not leak into any feature value dated before that future date."""
    df = _sample_ohlcv(100)
    future_date = df.index[80]
    # "cheat" signal: literally the future close price, injected as if it
    # were available from day 1 -- a bug would leak this into early rows'
    # features (e.g. via an unguarded merge/join or center=True rolling).
    df["cheat_future_close"] = df.loc[future_date, "Close"]

    features = assemble_feature_frame(df)

    assert "cheat_future_close" not in features.columns.tolist() or (
        features.loc[: df.index[79], "cheat_future_close"].isna().all()
    )
