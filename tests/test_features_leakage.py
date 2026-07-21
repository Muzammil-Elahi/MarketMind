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
    """Perturbing the raw ``Close`` price at a single *future* date must not
    change any feature value computed for a date before that future date.

    WR-03: the previous version of this test only asserted that a
    synthetic ``"cheat_future_close"`` column never appears in
    ``features.columns`` -- which is unconditionally true for *any*
    implementation of ``assemble_feature_frame`` (it always returns a fresh
    frame with exactly the four known feature columns and never passes
    through arbitrary input columns), so the check could never fail
    regardless of whether leakage existed. This version instead actually
    exercises the computation path: it perturbs a real future ``Close``
    value the four ``technical.*`` functions all read from, and asserts
    every feature value dated before that perturbation is byte-for-byte
    unchanged -- a genuine second, independent angle on D-11 alongside
    ``test_truncation_invariance_no_future_data_changes_past_features``
    above (that test compares frames of different *lengths*; this one
    compares frames of the *same* length with one future value changed).
    """
    df = _sample_ohlcv(100)
    future_date = df.index[80]

    baseline_features = assemble_feature_frame(df)

    perturbed_df = df.copy()
    # An extreme, unmistakable perturbation -- if any rolling/indicator
    # computation ever pulled this future value into an earlier row (e.g.
    # via an unguarded merge/join or a centered rolling window), the
    # assertion below would catch it.
    perturbed_df.loc[future_date, "Close"] *= 1000
    perturbed_features = assemble_feature_frame(perturbed_df)

    pd.testing.assert_frame_equal(
        baseline_features.loc[: df.index[79]],
        perturbed_features.loc[: df.index[79]],
    )
